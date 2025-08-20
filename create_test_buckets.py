#!/usr/bin/env python3
"""
Create S3 buckets for testing DTO analysis
"""
import boto3
import os
import sys
from botocore.exceptions import ClientError

def create_bucket(bucket_name, region='us-east-1'):
    """Create S3 bucket"""
    s3 = boto3.client('s3', region_name=region)
    
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✓ Created bucket: {bucket_name}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyExists':
            print(f"✓ Bucket {bucket_name} already exists")
            return True
        elif error_code == 'BucketAlreadyOwnedByYou':
            print(f"✓ Bucket {bucket_name} already owned by you")
            return True
        else:
            print(f"✗ Failed to create bucket {bucket_name}: {e}")
            return False

def main():
    """Create test buckets"""
    
    # Get AWS account ID for unique bucket names
    try:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
    except Exception as e:
        print(f"✗ Failed to get AWS account ID: {e}")
        return 1
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    # Generate unique bucket names
    cur_bucket = f"dto-test-cur-{account_id}"
    vpc_logs_bucket = f"dto-test-vpc-logs-{account_id}"
    
    print("Creating test S3 buckets for DTO analysis...")
    print(f"Region: {region}")
    print(f"CUR bucket: {cur_bucket}")
    print(f"VPC logs bucket: {vpc_logs_bucket}")
    print("-" * 50)
    
    success = True
    
    # Create buckets
    if not create_bucket(cur_bucket, region):
        success = False
    
    if not create_bucket(vpc_logs_bucket, region):
        success = False
    
    if success:
        print("\n" + "=" * 50)
        print("Buckets created successfully!")
        print("\nUpdate your environment variables:")
        print(f"export CUR_BUCKET={cur_bucket}")
        print(f"export VPC_LOGS_BUCKET={vpc_logs_bucket}")
        print("\nNext steps:")
        print("1. python generate_test_data.py")
        print("2. python run_dto_analysis.py")
        return 0
    else:
        print("\n✗ Failed to create some buckets")
        return 1

if __name__ == "__main__":
    sys.exit(main())