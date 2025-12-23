"""Core benchmarking functionality."""

import csv
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple


class BenchmarkConfig:
    """Configuration container for benchmark parameters."""
    
    def __init__(self) -> None:
        self.output_dir: Optional[Path] = None
        self.input_dir: Optional[Path] = None
        self.file_size: Optional[str] = None
        self.total_size: Optional[str] = None
        self.warmup: int = 3
        self.wait: int = 5
        self.out_file: Optional[Path] = None
        self.no_log: bool = False
        self.reuse_files: bool = False
        
        # Command templates
        self.put_cmd: Optional[str] = None
        self.get_cmd: Optional[str] = None
        self.del_cmd: Optional[str] = None


class FileGenerator:
    """Handles generation of test files for benchmarking."""
    
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
    
    def parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB', '1GB') to bytes."""
        size_str = size_str.upper().strip()
        
        # Define units in order of length (longest first to avoid partial matches)
        units = [('TB', 1024**4), ('GB', 1024**3), ('MB', 1024**2), ('KB', 1024), ('B', 1)]
        
        for unit, multiplier in units:
            if size_str.endswith(unit):
                number_part = size_str[:-len(unit)].strip()
                try:
                    return int(float(number_part) * multiplier)
                except ValueError:
                    raise ValueError(f"Invalid size format: {size_str}")
        
        # Try parsing as plain number (bytes)
        try:
            return int(size_str)
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}")
    
    def validate_disk_space(self, required_bytes: int) -> bool:
        """Validate available disk space before generation."""
        if not self.config.output_dir:
            return False
            
        # Get available disk space
        _, _, free_bytes = shutil.disk_usage(self.config.output_dir.parent)
        
        if free_bytes < required_bytes:
            print(f"Error: Insufficient disk space. Required: {required_bytes:,} bytes, Available: {free_bytes:,} bytes")
            return False
        
        return True
    
    def generate_files(self) -> List[Path]:
        """Generate reproducible random binary files."""
        if not self.config.output_dir or not self.config.file_size or not self.config.total_size:
            raise ValueError("Missing required parameters for file generation")
        
        # Parse sizes
        file_size_bytes = self.parse_size(self.config.file_size)
        total_size_bytes = self.parse_size(self.config.total_size)
        
        # Calculate number of files
        num_files = total_size_bytes // file_size_bytes
        if num_files == 0:
            raise ValueError(f"File size ({self.config.file_size}) is larger than total size ({self.config.total_size})")
        
        # Validate disk space
        if not self.validate_disk_space(total_size_bytes):
            raise RuntimeError("Insufficient disk space")
        
        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate files with fixed seed for reproducibility
        random.seed(42)
        generated_files = []
        
        print(f"Generating {num_files} files of {file_size_bytes:,} bytes each...")
        
        for i in range(num_files):
            filename = f"file_{i+1:04d}.bin"
            filepath = self.config.output_dir / filename
            
            # Generate random binary data
            with open(filepath, 'wb') as f:
                remaining = file_size_bytes
                chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                
                while remaining > 0:
                    chunk_size = min(chunk_size, remaining)
                    data = random.randbytes(chunk_size)
                    f.write(data)
                    remaining -= chunk_size
            
            generated_files.append(filepath)
        
        # Log generation summary
        actual_total = sum(f.stat().st_size for f in generated_files)
        print(f"Generated {len(generated_files)} files, total size: {actual_total:,} bytes")
        
        return generated_files


class BenchmarkRunner:
    """Handles execution of benchmark operations."""
    
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.results: List[Dict] = []
    
    def run_warmup(self, operation: str, files: List[Path]) -> None:
        """Run warm-up operations before measured benchmark."""
        if self.config.warmup <= 0:
            return
            
        cmd_template = self._get_command_template(operation)
        if not cmd_template:
            raise ValueError(f"No command template provided for {operation} operation")
        
        warmup_files = files[:self.config.warmup]
        
        for filepath in warmup_files:
            cmd = cmd_template.replace('{file}', str(filepath))
            success, error, latency_ns = self.execute_command(cmd, filepath.name)
            
            result = {
                'timestamp_ns': time.perf_counter_ns(),
                'operation': operation.upper(),
                'filename': filepath.name,
                'size_bytes': filepath.stat().st_size,
                'latency_ns': latency_ns,
                'status': 'success' if success else 'fail',
                'error': error,
                'warmup': True
            }
            
            self.log_result(result)
    
    def run_operation(self, operation: str, files: List[Path], is_warmup: bool = False) -> None:
        """Run benchmark operations and collect timing data."""
        cmd_template = self._get_command_template(operation)
        if not cmd_template:
            raise ValueError(f"No command template provided for {operation} operation")
        
        for filepath in files:
            cmd = cmd_template.replace('{file}', str(filepath))
            success, error, latency_ns = self.execute_command(cmd, filepath.name)
            
            result = {
                'timestamp_ns': time.perf_counter_ns(),
                'operation': operation.upper(),
                'filename': filepath.name,
                'size_bytes': filepath.stat().st_size,
                'latency_ns': latency_ns,
                'status': 'success' if success else 'fail',
                'error': error,
                'warmup': is_warmup
            }
            
            self.log_result(result)
            
            if not success:
                raise RuntimeError(f"Command failed: {error}")
    
    def execute_command(self, cmd: str, filename: str) -> Tuple[bool, str, int]:
        """Execute a single command and measure timing."""
        start_time = time.perf_counter_ns()
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, check=True
            )
            end_time = time.perf_counter_ns()
            return True, "", end_time - start_time
        except subprocess.CalledProcessError as e:
            end_time = time.perf_counter_ns()
            error_msg = e.stderr.strip() if e.stderr else str(e)
            return False, error_msg, end_time - start_time
    
    def log_result(self, result: Dict) -> None:
        """Log a single benchmark result."""
        self.results.append(result)
    
    def _get_command_template(self, operation: str) -> Optional[str]:
        """Get command template for operation."""
        if operation == 'put':
            return self.config.put_cmd
        elif operation == 'get':
            return self.config.get_cmd
        elif operation == 'delete':
            return self.config.del_cmd
        return None


class OutputWriter:
    """Handles writing benchmark results to files."""
    
    def __init__(self, output_path: Path, no_log: bool = False) -> None:
        self.output_path = output_path
        self.no_log = no_log
        self.buffer: List[Dict] = []
    
    def write_result(self, result: Dict) -> None:
        """Write a single result to output."""
        if self.no_log:
            return
            
        self.buffer.append(result)
        
        # Flush buffer when it gets large
        if len(self.buffer) >= 100:
            self.flush()
    
    def flush(self) -> None:
        """Flush buffered results to file."""
        if self.no_log or not self.buffer:
            return
            
        if self.output_path.suffix.lower() == '.csv':
            self._write_csv()
        else:
            self._write_jsonl()
        
        self.buffer.clear()
    
    def _write_csv(self) -> None:
        """Write results to CSV file."""
        file_exists = self.output_path.exists()
        
        with open(self.output_path, 'a', newline='') as f:
            if not self.buffer:
                return
                
            fieldnames = ['timestamp_ns', 'operation', 'filename', 'size_bytes', 
                         'latency_ns', 'status', 'error', 'warmup']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerows(self.buffer)
    
    def _write_jsonl(self) -> None:
        """Write results to JSON Lines file."""
        with open(self.output_path, 'a') as f:
            for result in self.buffer:
                json.dump(result, f)
                f.write('\n')


class ZBenchmarker:
    """Main benchmarker orchestrator."""
    
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.file_generator = FileGenerator(config)
        self.benchmark_runner = BenchmarkRunner(config)
        self.output_writer: Optional[OutputWriter] = None
        
        if config.out_file:
            self.output_writer = OutputWriter(config.out_file, config.no_log)
    
    def run_generate(self) -> List[Path]:
        """Run file generation mode."""
        return self.file_generator.generate_files()
    
    def run_benchmark(self, operation: str) -> None:
        """Run single operation benchmark mode."""
        if not self.config.input_dir or not self.config.input_dir.exists():
            raise ValueError("Input directory does not exist")
        
        # Get list of files to benchmark
        files = list(self.config.input_dir.glob('*.bin'))
        if not files:
            raise ValueError("No .bin files found in input directory")
        
        files.sort()  # Ensure consistent order
        
        print(f"Running {operation} benchmark on {len(files)} files...")
        
        # Run warmup phase
        self.benchmark_runner.run_warmup(operation, files)
        
        # Run main benchmark
        self.benchmark_runner.run_operation(operation, files)
        
        # Write results
        if self.output_writer:
            for result in self.benchmark_runner.results:
                self.output_writer.write_result(result)
            self.output_writer.flush()
        
        print(f"Completed {operation} benchmark")
    
    def run_full_cycle(self) -> None:
        """Run complete benchmark cycle (--ALL mode)."""
        print("Running full benchmark cycle")
        # TODO: Implement full cycle mode
        pass
    
    def validate_commands(self) -> None:
        """Validate that required commands are provided for --ALL mode."""
        # TODO: Implement command validation
        pass