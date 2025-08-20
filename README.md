# DTO Cost Analysis Agent

Analyzes AWS Data Transfer Out (DTO) costs using Cost and Usage Reports (CUR) and VPC Flow Logs.

## Setup

1. Install dependencies:
```bash
chmod +x setup.sh
./setup.sh
```

2. Configure AWS credentials and settings:
```bash
cp .env.example .env
# Edit .env with your actual values
```

3. Set environment variables:
```bash
export CUR_BUCKET=your-cur-bucket-name
export VPC_LOGS_BUCKET=your-vpc-logs-bucket
export TARGET_MONTH=2024-01
```

## Usage

Run the analysis:
```bash
python run_dto_analysis.py
```

Or use the agent directly:
```bash
python dto_strands_agent.py
```

## Features

- Analyzes top 10 most expensive DTO resources for a specific month
- Supports both text and parquet format VPC flow logs
- Generates AWS optimization recommendations
- Correlates CUR data with VPC flow logs for comprehensive analysis