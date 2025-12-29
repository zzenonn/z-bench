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
z-bench benchmark --op put --input-dir ./testfiles --put-cmd "aws s3 cp {file} s3://<bucket>/" --out results.csv

# GET benchmark  
z-bench benchmark --op get --input-dir ./testfiles --get-cmd "aws s3 cp s3://<bucket>/{filename} ./downloads/" --out results.csv

# DELETE benchmark
z-bench benchmark --op delete --input-dir ./testfiles --del-cmd "aws s3 rm s3://<bucket>/{filename}" --out results.csv
```

### 3. Full Cycle Benchmark

```bash
# Generate new files and run full cycle
z-bench --ALL --output-dir ./testfiles --file-size 10MB --total-size 1GB \
  --put-cmd "aws s3 cp {file} s3://<bucket>/" \
  --get-cmd "aws s3 cp s3://<bucket>/{filename} ./downloads/" \
  --del-cmd "aws s3 rm s3://<bucket>/{filename}" \
  --out results.csv

# Use existing files and run full cycle
z-bench --ALL --input-dir ./existing-files \
  --put-cmd "aws s3 cp {file} s3://<bucket>/" \
  --get-cmd "aws s3 cp s3://<bucket>/{filename} ./downloads/" \
  --del-cmd "aws s3 rm s3://<bucket>/{filename}" \
  --out results.csv
```

**Note:** Replace `<bucket>` with your actual bucket name in the command templates.

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

- `--input-dir DIR` - Use existing files (skips generation)
- `--output-dir DIR` - Directory for generated files (if not using --input-dir)
- `--file-size SIZE` - Size per file (for generation)
- `--total-size SIZE` - Total dataset size (for generation)
- `--put-cmd CMD` - PUT command template
- `--get-cmd CMD` - GET command template
- `--del-cmd CMD` - DELETE command template
- `--reuse-files` - Skip file generation if files already exist

## Command Templates

Use placeholders in command templates:

- `{file}` - **Full file path** (e.g., `./testfiles/file_0001.bin`) - use for PUT operations
- `{filename}` - **Just filename** (e.g., `file_0001.bin`) - use for GET/DELETE operations
- `<bucket>` - **Manual replacement** required - replace with your actual bucket name

### Usage by Operation:
- **PUT**: Use `{file}` to read from local filesystem
- **GET**: Use `{filename}` to match S3 object keys
- **DELETE**: Use `{filename}` to match S3 object keys

Examples:
- PUT: `aws s3 cp {file} s3://my-bucket/`
- GET: `aws s3 cp s3://my-bucket/{filename} ./downloads/`
- DELETE: `aws s3 rm s3://my-bucket/{filename}`

## Output Format

Results are logged per-operation with the following fields:

| Field | Description |
|-------|-------------|
| `timestamp_ns` | Monotonic start timestamp (nanoseconds since system boot) |
| `operation` | Operation type: PUT, GET, or DELETE |
| `filename` | Name of the test file (e.g., file_0001.bin) |
| `size_bytes` | File size in bytes |
| `latency_ns` | **Total completion time** of the command execution in nanoseconds |
| `status` | Operation result: success or fail |
| `error` | Error message from stderr if operation failed (empty if successful) |
| `warmup` | Whether this was a warmup operation: true or false |

### Field Details

- **`latency_ns`**: Measures the complete execution time of the storage command from start to finish, including network transfer, authentication, and storage system processing
- **`timestamp_ns`**: Uses `time.perf_counter_ns()` for high-precision, monotonic timing that's not affected by system clock adjustments
- **`size_bytes`**: Actual file size on disk, useful for calculating throughput (bytes/second)
- **`warmup`**: Warmup operations help "prime" the system and are excluded from performance analysis

## Performance Features

- Minimal overhead timing using `time.perf_counter_ns()`
- Warm-up phases for realistic measurements
- Buffered logging to reduce I/O impact
- No progress bars or summaries during execution
- Sequential execution for consistent results

## Examples

### AWS S3 Full Benchmark (Generate Files)

```bash
z-bench --ALL \
  --output-dir ./testfiles \
  --file-size 50MB \
  --total-size 2GB \
  --put-cmd "aws s3 cp {file} s3://my-test-bucket/" \
  --get-cmd "aws s3 cp s3://my-test-bucket/{filename} ./downloads/" \
  --del-cmd "aws s3 rm s3://my-test-bucket/{filename}" \
  --out s3-benchmark.csv \
  --warmup 5 \
  --wait 10
```

### AWS S3 Full Benchmark (Use Existing Files)

```bash
z-bench --ALL \
  --input-dir ./existing-testfiles \
  --put-cmd "aws s3 cp {file} s3://my-test-bucket/" \
  --get-cmd "aws s3 cp s3://my-test-bucket/{filename} ./downloads/" \
  --del-cmd "aws s3 rm s3://my-test-bucket/{filename}" \
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