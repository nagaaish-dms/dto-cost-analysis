#!/usr/bin/env python3
import asyncio
import json
import os
from dto_strands_agent import DTOCostAnalysisAgent

async def main():
    agent = DTOCostAnalysisAgent()
    
    # Get configuration from environment variables or use defaults
    cur_bucket = os.getenv('CUR_BUCKET', 'your-cur-bucket-name')
    cur_prefix = os.getenv('CUR_PREFIX', 'cur-reports/')
    target_month = os.getenv('TARGET_MONTH', '2024-01')
    vpc_logs_bucket = os.getenv('VPC_LOGS_BUCKET', 'your-vpc-logs-bucket')
    vpc_logs_prefix = os.getenv('VPC_LOGS_PREFIX', 'vpc-flow-logs/')
    top_n = int(os.getenv('TOP_N', '10'))
    
    print(f"Analyzing DTO costs for {target_month}...")
    print(f"CUR Bucket: {cur_bucket}")
    print(f"VPC Logs Bucket: {vpc_logs_bucket}")
    print("-" * 50)
    
    try:
        result = await agent.run_complete_analysis(
            cur_bucket=cur_bucket,
            cur_prefix=cur_prefix,
            target_month=target_month,
            vpc_logs_bucket=vpc_logs_bucket,
            vpc_logs_prefix=vpc_logs_prefix,
            top_n=top_n
        )
        
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"Error running analysis: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)