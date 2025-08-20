#!/usr/bin/env python3
"""
Test setup script to validate customer environment before running DTO analysis
"""
import boto3
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError

def test_aws_credentials():
    """Test AWS credentials and basic connectivity"""
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ AWS credentials valid - Account: {identity['Account']}")
        return True
    except NoCredentialsError:
        print("✗ AWS credentials not found. Run 'aws configure' or set environment variables")
        return False
    except Exception as e:
        print(f"✗ AWS credential error: {e}")
        return False

def test_s3_bucket_access(bucket_name, prefix=""):
    """Test S3 bucket access"""
    try:
        s3 = boto3.client('s3')
        s3.head_bucket(Bucket=bucket_name)
        
        # Try to list objects
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, MaxKeys=1)
        file_count = response.get('KeyCount', 0)
        
        print(f"✓ S3 bucket '{bucket_name}' accessible - {file_count} files found with prefix '{prefix}'")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"✗ S3 bucket '{bucket_name}' not found")
        elif error_code == '403':
            print(f"✗ Access denied to S3 bucket '{bucket_name}'")
        else:
            print(f"✗ S3 error for bucket '{bucket_name}': {e}")
        return False

def test_environment_variables():
    """Test required environment variables"""
    required_vars = ['CUR_BUCKET', 'TARGET_MONTH']
    optional_vars = ['VPC_LOGS_BUCKET', 'CUR_PREFIX', 'VPC_LOGS_PREFIX']
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"✗ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    print("✓ Required environment variables set")
    
    # Show optional variables
    for var in optional_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    return True

def main():
    """Run all tests"""
    print("DTO Cost Analysis Agent - Environment Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: AWS Credentials
    total_tests += 1
    if test_aws_credentials():
        tests_passed += 1
    
    # Test 2: Environment Variables
    total_tests += 1
    if test_environment_variables():
        tests_passed += 1
    
    # Test 3: CUR Bucket Access
    cur_bucket = os.getenv('CUR_BUCKET')
    if cur_bucket:
        total_tests += 1
        cur_prefix = os.getenv('CUR_PREFIX', '')
        if test_s3_bucket_access(cur_bucket, cur_prefix):
            tests_passed += 1
    
    # Test 4: VPC Logs Bucket Access (optional)
    vpc_bucket = os.getenv('VPC_LOGS_BUCKET')
    if vpc_bucket and vpc_bucket != 'dummy-bucket':
        total_tests += 1
        vpc_prefix = os.getenv('VPC_LOGS_PREFIX', '')
        if test_s3_bucket_access(vpc_bucket, vpc_prefix):
            tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ Environment ready! You can run: python run_dto_analysis.py")
        return 0
    else:
        print("✗ Please fix the issues above before running the analysis")
        return 1

if __name__ == "__main__":
    sys.exit(main())