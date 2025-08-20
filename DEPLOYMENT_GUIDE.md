# DTO Cost Analysis Agent - Customer Deployment Guide

## Prerequisites

### 1. AWS Account Setup
- AWS account with billing data (CUR) enabled
- VPC Flow Logs configured and stored in S3
- IAM permissions for S3 access

### 2. Required AWS Services
- **Cost and Usage Reports (CUR)**: Must be enabled and delivered to S3
- **VPC Flow Logs**: Must be configured to deliver to S3 (text or parquet format)

## Quick Start

### Step 1: Clone and Setup
```bash
git clone <repository-url>
cd dto-cost-analysis
chmod +x setup.sh
./setup.sh
```

### Step 2: Configure AWS Credentials
```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### Step 3: Configure Analysis Parameters
```bash
cp .env.example .env
# Edit .env with your bucket names and settings
```

### Step 4: Run Analysis
```bash
python run_dto_analysis.py
```

## Detailed Configuration

### Required IAM Permissions
Create an IAM policy with these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-cur-bucket/*",
                "arn:aws:s3:::your-cur-bucket",
                "arn:aws:s3:::your-vpc-logs-bucket/*",
                "arn:aws:s3:::your-vpc-logs-bucket"
            ]
        }
    ]
}
```

### Environment Variables
```bash
# Required
export CUR_BUCKET=your-billing-bucket-name
export VPC_LOGS_BUCKET=your-vpc-logs-bucket-name
export TARGET_MONTH=2024-01

# Optional
export CUR_PREFIX=cur-reports/
export VPC_LOGS_PREFIX=vpc-flow-logs/
export TOP_N=10
export AWS_REGION=us-east-1
```

## Testing with Sample Data

### Option 1: Quick Test with Dummy Data (Recommended)
```bash
# Complete test setup with generated data
./test_with_dummy_data.sh
```

This will:
1. Create test S3 buckets with unique names
2. Generate realistic CUR data and VPC flow logs
3. Run the complete analysis
4. Show cleanup commands

### Option 2: Manual Dummy Data Setup
```bash
# Create test buckets
python create_test_buckets.py

# Set environment variables (use output from above)
export CUR_BUCKET=dto-test-cur-123456789012
export VPC_LOGS_BUCKET=dto-test-vpc-logs-123456789012
export TARGET_MONTH=2024-01

# Generate test data
python generate_test_data.py

# Run analysis
python run_dto_analysis.py
```

### Option 3: Use Your Real Data

1. **Enable Cost and Usage Reports**:
   - Go to AWS Billing Console → Cost & Usage Reports
   - Create new report with S3 delivery

2. **Enable VPC Flow Logs**:
   ```bash
   aws ec2 create-flow-logs \
     --resource-type VPC \
     --resource-ids vpc-12345678 \
     --traffic-type ALL \
     --log-destination-type s3 \
     --log-destination arn:aws:s3:::your-vpc-logs-bucket/vpc-flow-logs/
   ```

### Test with Minimal Setup
```bash
# Test with just CUR data (VPC logs optional)
export CUR_BUCKET=your-billing-bucket
export VPC_LOGS_BUCKET=dummy-bucket  # Will gracefully handle missing data
export TARGET_MONTH=2024-01

python run_dto_analysis.py
```

## Expected Output

```json
{
  "status": "success",
  "analysis_summary": {
    "target_month": "2024-01",
    "total_dto_cost": 1234.56,
    "resources_analyzed": 10,
    "flow_logs_status": "success",
    "recommendations_count": 5
  },
  "expensive_resources": [...],
  "flow_analysis": {...},
  "recommendations": [...]
}
```

## Troubleshooting

### Common Issues:

1. **"No CUR data found"**
   - Verify CUR is enabled and delivered to S3
   - Check bucket name and prefix
   - Ensure target month has data

2. **"Access Denied"**
   - Verify IAM permissions
   - Check AWS credentials configuration

3. **"No VPC flow logs"**
   - VPC logs are optional - analysis will continue
   - Verify VPC Flow Logs are enabled and delivered to S3

### Debug Mode
```bash
export DEBUG=true
python run_dto_analysis.py
```

## Cost Considerations

- **S3 API calls**: ~$0.0004 per 1,000 requests
- **Data transfer**: Minimal (reading existing data)
- **Compute**: Runs locally, no AWS compute charges

## Next Steps

1. Review generated recommendations
2. Implement suggested optimizations
3. Schedule monthly analysis
4. Monitor cost improvements

## Support

For issues or questions:
1. Check troubleshooting section
2. Review AWS service documentation
3. Verify IAM permissions and bucket access