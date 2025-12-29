#!/usr/bin/env python3
"""Command line interface for z_bench."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core import ZBenchmarker, BenchmarkConfig


def validate_python_version() -> None:
    """Ensure Python version >= 3.9."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required", file=sys.stderr)
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="z_bench - Object Storage Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate test files
  %(prog)s generate --output-dir ./testfiles --file-size 10MB --total-size 1GB
  
  # Benchmark PUT operations
  %(prog)s benchmark --op put --input-dir ./testfiles --put-cmd "aws s3 cp {file} s3://bucket/"
  
  # Full benchmark cycle
  %(prog)s --ALL --output-dir ./testfiles --file-size 10MB --total-size 1GB
        """
    )
    
    # Mode selection
    subparsers = parser.add_subparsers(dest='mode', help='Operation modes')
    
    # Add --ALL as a top-level option
    parser.add_argument('--ALL', action='store_true',
                       help='Run full benchmark cycle (generate → PUT → GET → DELETE)')
    
    # Generate mode
    gen_parser = subparsers.add_parser('generate', help='Generate test files')
    gen_parser.add_argument('--output-dir', type=Path, required=True,
                           help='Directory for generated files')
    gen_parser.add_argument('--file-size', required=True,
                           help='Size per file (e.g., 10MB)')
    gen_parser.add_argument('--total-size', required=True,
                           help='Total dataset size (e.g., 1GB)')
    
    # Benchmark mode
    bench_parser = subparsers.add_parser('benchmark', help='Run benchmark operations')
    bench_parser.add_argument('--op', choices=['put', 'get', 'delete'], required=True,
                             help='Operation type to benchmark')
    bench_parser.add_argument('--input-dir', type=Path, required=True,
                             help='Directory containing test files')
    
    # Command templates
    for parser_obj in [parser, bench_parser]:
        parser_obj.add_argument('--put-cmd', help='PUT command template')
        parser_obj.add_argument('--get-cmd', help='GET command template')
        parser_obj.add_argument('--del-cmd', help='DELETE command template')
        parser_obj.add_argument('--out', type=Path, default='results.csv',
                               help='Output file (CSV or JSONL)')
        parser_obj.add_argument('--warmup', type=int, default=3,
                               help='Number of warm-up operations per type')
        parser_obj.add_argument('--wait', type=int, default=5,
                               help='Wait time between phases (seconds)')
        parser_obj.add_argument('--no-log', action='store_true',
                               help='Disable logging for ultra-low-overhead timing')
    parser.add_argument('--reuse-files', action='store_true',
                       help='Skip file generation if files exist (--ALL mode)')
    
    # Full cycle mode options
    parser.add_argument('--output-dir', type=Path,
                       help='Directory for generated files (--ALL mode)')
    parser.add_argument('--input-dir', type=Path,
                       help='Directory with existing files (--ALL mode, skips generation)')
    parser.add_argument('--file-size',
                       help='Size per file (--ALL mode)')
    parser.add_argument('--total-size',
                       help='Total dataset size (--ALL mode)')
    
    args = parser.parse_args()
    
    # Validate that either --ALL or a subcommand is provided
    if not args.ALL and not args.mode:
        parser.error('Must specify either --ALL or a subcommand (generate/benchmark)')
    
    return args


def create_config(args: argparse.Namespace) -> BenchmarkConfig:
    """Create configuration from parsed arguments."""
    config = BenchmarkConfig()
    
    # Set configuration from arguments
    config.output_dir = args.output_dir
    config.file_size = args.file_size
    config.total_size = args.total_size
    config.warmup = args.warmup
    config.wait = args.wait
    config.out_file = args.out
    config.no_log = args.no_log
    config.reuse_files = args.reuse_files
    
    # Command templates
    config.put_cmd = args.put_cmd
    config.get_cmd = args.get_cmd
    config.del_cmd = args.del_cmd
    
    # Set input_dir for benchmark mode or --ALL mode
    if hasattr(args, 'input_dir') and args.input_dir:
        config.input_dir = args.input_dir
    elif args.ALL and args.input_dir:
        config.input_dir = args.input_dir
    
    return config


def main() -> None:
    """Main entry point."""
    validate_python_version()
    
    args = parse_arguments()
    config = create_config(args)
    
    try:
        benchmarker = ZBenchmarker(config)
        
        if args.ALL:
            benchmarker.run_full_cycle()
        elif args.mode == 'generate':
            benchmarker.run_generate()
        elif args.mode == 'benchmark':
            benchmarker.run_benchmark(args.op)
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()