#!/usr/bin/env python3
"""
Generate dummy CUR data and VPC flow logs for testing DTO analysis
"""
import pandas as pd
import boto3
import os
import random
from datetime import datetime, timedelta
import gzip
import io

def generate_cur_data(target_month="2024-01"):
    """Generate dummy CUR data with DTO costs"""
    
    # Sample resource IDs and services
    resources = [
        ("i-1234567890abcdef0", "Amazon Elastic Compute Cloud", "us-east-1"),
        ("i-0987654321fedcba0", "Amazon Elastic Compute Cloud", "us-west-2"),
        ("vol-1234567890abcdef0", "Amazon Elastic Block Store", "us-east-1"),
        ("natgw-1234567890abcdef0", "Amazon Virtual Private Cloud", "us-east-1"),
        ("igw-1234567890abcdef0", "Amazon Virtual Private Cloud", "us-east-1"),
        ("db-instance-1", "Amazon Relational Database Service", "us-east-1"),
        ("bucket-name-123", "Amazon Simple Storage Service", "us-east-1"),
        ("cf-distribution-123", "Amazon CloudFront", "Global"),
        ("lb-1234567890abcdef0", "Elastic Load Balancing", "us-east-1"),
        ("eni-1234567890abcdef0", "Amazon Virtual Private Cloud", "us-east-1")
    ]
    
    # Generate CUR records
    records = []
    start_date = datetime.strptime(f"{target_month}-01", "%Y-%m-%d")
    
    for day in range(1, 29):  # 28 days of data
        current_date = start_date + timedelta(days=day-1)
        date_str = current_date.strftime("%Y-%m-%d")
        
        for resource_id, service, region in resources:
            # Generate multiple DTO-related usage types per resource
            usage_types = [
                f"{region}-DataTransfer-Out-Bytes",
                f"{region}-DataTransfer-Regional-Bytes", 
                f"DataTransfer-Out-Bytes",
                f"{region}-NatGateway-Bytes"
            ]
            
            for usage_type in usage_types:
                if random.random() < 0.7:  # 70% chance of having this usage type
                    cost = round(random.uniform(5, 500), 2)
                    usage_amount = round(cost * random.uniform(100, 1000), 2)
                    
                    records.append({
                        'lineItem/usageStartDate': date_str,
                        'lineItem/usageEndDate': date_str,
                        'lineItem/resourceId': resource_id,
                        'lineItem/usageType': usage_type,
                        'lineItem/blendedCost': cost,
                        'lineItem/usageAmount': usage_amount,
                        'product/serviceName': service,
                        'product/region': region,
                        'product/productFamily': 'Data Transfer' if 'DataTransfer' in usage_type else 'Compute Instance'
                    })
    
    return pd.DataFrame(records)

def generate_vpc_flow_logs(resource_ids, target_month="2024-01"):
    """Generate dummy VPC flow logs"""
    
    # Extract IP addresses from resource IDs (simplified)
    ip_mappings = {
        "i-1234567890abcdef0": "10.0.1.100",
        "i-0987654321fedcba0": "10.0.2.200", 
        "natgw-1234567890abcdef0": "10.0.1.1",
        "igw-1234567890abcdef0": "10.0.0.1",
        "eni-1234567890abcdef0": "10.0.1.50"
    }
    
    external_ips = ["203.0.113.1", "198.51.100.1", "192.0.2.1", "8.8.8.8", "1.1.1.1"]
    
    logs = []
    start_date = datetime.strptime(f"{target_month}-01", "%Y-%m-%d")
    
    for day in range(1, 8):  # 7 days of flow logs
        current_date = start_date + timedelta(days=day-1)
        timestamp = int(current_date.timestamp())
        
        for _ in range(100):  # 100 flows per day
            src_ip = random.choice(list(ip_mappings.values()) + external_ips)
            dst_ip = random.choice(list(ip_mappings.values()) + external_ips)
            
            # Ensure some flows involve our resources
            if random.random() < 0.6:
                if random.random() < 0.5:
                    src_ip = random.choice(list(ip_mappings.values()))
                else:
                    dst_ip = random.choice(list(ip_mappings.values()))
            
            bytes_transferred = random.randint(1000, 100000000)  # 1KB to 100MB
            protocol = random.choice([6, 17, 1])  # TCP, UDP, ICMP
            
            # VPC Flow Log format: version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes windowstart windowend action flowlogstatus
            log_entry = f"2 123456789012 eni-1234567890abcdef0 {src_ip} {dst_ip} {random.randint(1024, 65535)} {random.choice([80, 443, 22, 3306, 5432])} {protocol} {random.randint(1, 100)} {bytes_transferred} {timestamp} {timestamp + 60} ACCEPT OK"
            logs.append(log_entry)
    
    return logs

def upload_to_s3(bucket_name, key, content, is_gzip=False):
    """Upload content to S3"""
    s3 = boto3.client('s3')
    
    if is_gzip:
        # Compress content
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(content.encode('utf-8'))
        content = buffer.getvalue()
    
    try:
        if isinstance(content, str):
            s3.put_object(Bucket=bucket_name, Key=key, Body=content.encode('utf-8'))
        else:
            s3.put_object(Bucket=bucket_name, Key=key, Body=content)
        print(f"✓ Uploaded {key} to s3://{bucket_name}/")
        return True
    except Exception as e:
        print(f"✗ Failed to upload {key}: {e}")
        return False

def main():
    """Generate and upload test data"""
    
    # Configuration
    target_month = os.getenv('TARGET_MONTH', '2024-01')
    cur_bucket = os.getenv('CUR_BUCKET', 'test-cur-bucket')
    vpc_logs_bucket = os.getenv('VPC_LOGS_BUCKET', 'test-vpc-logs-bucket')
    
    print("Generating dummy test data for DTO analysis...")
    print(f"Target month: {target_month}")
    print(f"CUR bucket: {cur_bucket}")
    print(f"VPC logs bucket: {vpc_logs_bucket}")
    print("-" * 50)
    
    # Generate CUR data
    print("Generating CUR data...")
    cur_df = generate_cur_data(target_month)
    cur_csv = cur_df.to_csv(index=False)
    
    # Upload CUR data
    cur_key = f"cur-reports/cur-{target_month}/cur-data.csv.gz"
    upload_to_s3(cur_bucket, cur_key, cur_csv, is_gzip=True)
    
    # Generate VPC flow logs
    print("Generating VPC flow logs...")
    resource_ids = cur_df['lineItem/resourceId'].unique()
    flow_logs = generate_vpc_flow_logs(resource_ids, target_month)
    flow_logs_content = '\n'.join(flow_logs)
    
    # Upload VPC flow logs (text format)
    vpc_key = f"vpc-flow-logs/{target_month}/flow-logs.txt"
    upload_to_s3(vpc_logs_bucket, vpc_key, flow_logs_content)
    
    # Also create parquet version
    print("Generating parquet VPC flow logs...")
    flow_records = []
    for log in flow_logs:
        fields = log.split()
        if len(fields) >= 14:
            flow_records.append({
                'srcaddr': fields[3],
                'dstaddr': fields[4],
                'srcport': int(fields[5]),
                'dstport': int(fields[6]),
                'protocol': int(fields[7]),
                'bytes': int(fields[9])
            })
    
    flow_df = pd.DataFrame(flow_records)
    
    # Save parquet to local file then upload
    parquet_file = f"/tmp/flow-logs-{target_month}.parquet"
    flow_df.to_parquet(parquet_file)
    
    with open(parquet_file, 'rb') as f:
        parquet_content = f.read()
    
    vpc_parquet_key = f"vpc-flow-logs/{target_month}/flow-logs.parquet"
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=vpc_logs_bucket, Key=vpc_parquet_key, Body=parquet_content)
        print(f"✓ Uploaded {vpc_parquet_key} to s3://{vpc_logs_bucket}/")
    except Exception as e:
        print(f"✗ Failed to upload parquet: {e}")
    
    # Clean up temp file
    os.remove(parquet_file)
    
    print("\n" + "=" * 50)
    print("Test data generation complete!")
    print(f"CUR records: {len(cur_df)}")
    print(f"VPC flow logs: {len(flow_logs)}")
    print("\nYou can now run: python run_dto_analysis.py")

if __name__ == "__main__":
    main()