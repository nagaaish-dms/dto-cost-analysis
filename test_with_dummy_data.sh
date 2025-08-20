#!/bin/bash
set -e

echo "DTO Cost Analysis - Complete Test Setup"
echo "======================================"

# Set default values
export TARGET_MONTH=${TARGET_MONTH:-2024-01}
export AWS_REGION=${AWS_REGION:-us-east-1}

echo "Target month: $TARGET_MONTH"
echo "AWS region: $AWS_REGION"
echo ""

# Step 1: Create test buckets
echo "Step 1: Creating test S3 buckets..."
python create_test_buckets.py

if [ $? -ne 0 ]; then
    echo "Failed to create buckets. Exiting."
    exit 1
fi

# Get bucket names from the output (simple approach)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CUR_BUCKET="dto-test-cur-$ACCOUNT_ID"
export VPC_LOGS_BUCKET="dto-test-vpc-logs-$ACCOUNT_ID"

echo ""
echo "Step 2: Generating dummy test data..."
python generate_test_data.py

if [ $? -ne 0 ]; then
    echo "Failed to generate test data. Exiting."
    exit 1
fi

echo ""
echo "Step 3: Running DTO analysis..."
python run_dto_analysis.py

echo ""
echo "======================================"
echo "Test complete!"
echo ""
echo "To clean up test resources:"
echo "aws s3 rb s3://$CUR_BUCKET --force"
echo "aws s3 rb s3://$VPC_LOGS_BUCKET --force"