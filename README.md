# z_bench - Object Storage Benchmark

A professional benchmarking tool for object storage systems that provides accurate performance measurements with minimal overhead.

## Requirements

- Python >= 3.9
- Standard libraries only (no external dependencies)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd object-storage-benchmarker

# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Or using pip
pip install -e .
```

## Usage

## Quick Start

### 1. Generate Test Files

```bash
z-bench generate --output-dir ./testfiles --file-size 10MB --total-size 1GB
```

### 2. Benchmark Individual Operations

```bash
# PUT benchmark
z-bench benchmark --op put --input-dir ./testfiles --put-cmd "aws s3 cp {file} s3://{bucket}/" --out results.csv

# GET benchmark  
z-bench benchmark --op get --input-dir ./testfiles --get-cmd "aws s3 cp s3://{bucket}/{file} ./downloads/" --out results.csv

# DELETE benchmark
z-bench benchmark --op delete --input-dir ./testfiles --del-cmd "aws s3 rm s3://{bucket}/{file}" --out results.csv
```

### 3. Full Cycle Benchmark

```bash
z-bench --ALL --output-dir ./testfiles --file-size 10MB --total-size 1GB --out results.csv
```

## Development Mode

To run without installation:

```bash
# Using module syntax from project root
python -m src.z_bench.cli generate --output-dir ./testfiles --file-size 10MB --total-size 1GB

# Check help
python -m src.z_bench.cli --help
```

## Command Reference

### Global Options

- `--out FILE` - Output file (CSV or JSONL format)
- `--warmup N` - Number of warm-up operations per operation type (default: 3)
- `--wait N` - Wait time between operation phases in seconds (default: 5)
- `--no-log` - Disable logging for ultra-low-overhead timing

### Generate Mode

```bash
z-bench generate [OPTIONS]
```

- `--output-dir DIR` - Directory for generated files
- `--file-size SIZE` - Size per file (e.g., 10MB, 1GB)
- `--total-size SIZE` - Total dataset size

### Benchmark Mode

```bash
z-bench benchmark [OPTIONS]
```

- `--op {put|get|delete}` - Operation type to benchmark
- `--input-dir DIR` - Directory containing test files
- `--put-cmd CMD` - PUT command template
- `--get-cmd CMD` - GET command template  
- `--del-cmd CMD` - DELETE command template

### Full Cycle Mode

```bash
z-bench --ALL [OPTIONS]
```

Combines generation and all benchmark operations with automatic sequencing.

- `--reuse-files` - Skip file generation if files already exist

## Command Templates

Use placeholders in command templates:

- `{file}` - File name or path
- `{bucket}` - Bucket name (you need to specify this in your commands)

Examples:
- AWS S3: `aws s3 cp {file} s3://mybucket/`
- MinIO: `mc cp {file} myminio/mybucket/`
- Azure: `az storage blob upload --file {file} --container mybucket`

## Output Format

Results are logged per-operation with the following fields:

| Field | Description |
|-------|-------------|
| `timestamp_ns` | Monotonic start timestamp |
| `operation` | PUT / GET / DELETE |
| `filename` | File name or path |
| `size_bytes` | File size |
| `latency_ns` | Duration of operation |
| `status` | success / fail |
| `error` | Error message if failed |
| `warmup` | true / false |

## Performance Features

- Minimal overhead timing using `time.perf_counter_ns()`
- Warm-up phases for realistic measurements
- Buffered logging to reduce I/O impact
- No progress bars or summaries during execution
- Sequential execution for consistent results

## Examples

### AWS S3 Full Benchmark

```bash
z-bench --ALL \
  --output-dir ./testfiles \
  --file-size 50MB \
  --total-size 2GB \
  --put-cmd "aws s3 cp {file} s3://my-test-bucket/" \
  --get-cmd "aws s3 cp s3://my-test-bucket/{file} ./downloads/" \
  --del-cmd "aws s3 rm s3://my-test-bucket/{file}" \
  --out s3-benchmark.csv \
  --warmup 5 \
  --wait 10
```

### MinIO Benchmark

```bash
z-bench benchmark --op put \
  --input-dir ./testfiles \
  --put-cmd "mc cp {file} local/testbucket/" \
  --out minio-put.jsonl
```