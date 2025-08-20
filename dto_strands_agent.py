#!/usr/bin/env python3
from strands import Agent, task
import boto3
import pandas as pd
from typing import Dict, List, Any
import json
from datetime import datetime, timedelta
import asyncio

class DTOCostAnalysisAgent(Agent):
    def __init__(self):
        super().__init__(
            name="DTO Cost Analysis Agent",
            description="Analyzes Data Transfer Out costs using CUR data and VPC Flow Logs"
        )
        self.s3_client = boto3.client('s3')
        self.logs_client = boto3.client('logs')

    @task
    async def analyze_expensive_dto_resources(self, cur_bucket: str, cur_prefix: str, target_month: str, top_n: int = 10) -> List[Dict]:
        """Extract most expensive DTO resources from CUR data for specific month"""
        response = self.s3_client.list_objects_v2(Bucket=cur_bucket, Prefix=cur_prefix)
        
        cur_data = []
        for obj in response.get('Contents', []):
            if obj['Key'].endswith(('.csv', '.csv.gz')) and target_month in obj['Key']:
                obj_response = self.s3_client.get_object(Bucket=cur_bucket, Key=obj['Key'])
                df = pd.read_csv(obj_response['Body'], compression='gzip' if obj['Key'].endswith('.gz') else None)
                cur_data.append(df)
        
        if not cur_data:
            return []
        
        combined_df = pd.concat(cur_data, ignore_index=True)
        
        # Filter for specific month and data transfer costs
        if 'lineItem/usageStartDate' in combined_df.columns:
            combined_df['month'] = pd.to_datetime(combined_df['lineItem/usageStartDate']).dt.strftime('%Y-%m')
            combined_df = combined_df[combined_df['month'] == target_month]
        
        dto_df = combined_df[
            (combined_df.get('product/productFamily', '').str.contains('Data Transfer', na=False)) |
            (combined_df.get('lineItem/usageType', '').str.contains('DataTransfer', na=False))
        ]
        
        # Group by resource and calculate monthly costs
        expensive_resources = dto_df.groupby([
            'lineItem/resourceId', 
            'product/serviceName',
            'product/region'
        ]).agg({
            'lineItem/blendedCost': 'sum',
            'lineItem/usageAmount': 'sum'
        }).reset_index()
        
        return expensive_resources.nlargest(top_n, 'lineItem/blendedCost').to_dict('records')

    @task
    async def correlate_vpc_flow_logs(self, resource_ids: List[str], s3_bucket: str, s3_prefix: str = "vpc-flow-logs/") -> Dict[str, Any]:
        """Analyze VPC flow logs from S3 text files for expensive resources"""
        if not resource_ids:
            return {'status': 'no_resources'}
        
        try:
            # List VPC flow log files in S3
            response = self.s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix)
            
            if 'Contents' not in response:
                return {'status': 'no_files', 'error': 'No VPC flow log files found'}
            
            flows_data = []
            resource_set = set(resource_ids)
            
            # Process flow log files
            for obj in response['Contents'][:10]:  # Limit to 10 files for performance
                if obj['Key'].endswith(('.txt', '.log')):
                    # Handle text format
                    obj_response = self.s3_client.get_object(Bucket=s3_bucket, Key=obj['Key'])
                    content = obj_response['Body'].read().decode('utf-8')
                    
                    for line in content.strip().split('\n'):
                        if line.strip():
                            fields = line.split()
                            if len(fields) >= 14:  # Standard VPC flow log format
                                srcaddr = fields[3]
                                dstaddr = fields[4]
                                bytes_transferred = int(fields[10]) if fields[10].isdigit() else 0
                                protocol = fields[7]
                                
                                # Check if any resource ID matches source or destination
                                if any(rid in srcaddr or rid in dstaddr for rid in resource_set):
                                    flows_data.append({
                                        'srcaddr': srcaddr,
                                        'dstaddr': dstaddr,
                                        'bytes': bytes_transferred,
                                        'protocol': protocol
                                    })
                
                elif obj['Key'].endswith('.parquet'):
                    # Handle parquet format
                    obj_response = self.s3_client.get_object(Bucket=s3_bucket, Key=obj['Key'])
                    df = pd.read_parquet(obj_response['Body'])
                    
                    # Filter for matching resource IDs
                    mask = df['srcaddr'].isin(resource_set) | df['dstaddr'].isin(resource_set)
                    filtered_df = df[mask]
                    
                    for _, row in filtered_df.iterrows():
                        flows_data.append({
                            'srcaddr': str(row['srcaddr']),
                            'dstaddr': str(row['dstaddr']),
                            'bytes': int(row['bytes']) if pd.notna(row['bytes']) else 0,
                            'protocol': str(row['protocol'])
                        })
            
            # Aggregate flows by source/destination pairs
            flow_summary = {}
            for flow in flows_data:
                key = f"{flow['srcaddr']}-{flow['dstaddr']}-{flow['protocol']}"
                if key not in flow_summary:
                    flow_summary[key] = {
                        'srcaddr': flow['srcaddr'],
                        'dstaddr': flow['dstaddr'],
                        'protocol': flow['protocol'],
                        'total_bytes': 0,
                        'flow_count': 0
                    }
                flow_summary[key]['total_bytes'] += flow['bytes']
                flow_summary[key]['flow_count'] += 1
            
            # Sort by total bytes and return top flows
            sorted_flows = sorted(flow_summary.values(), key=lambda x: x['total_bytes'], reverse=True)[:100]
            
            return {
                'status': 'success',
                'flows': sorted_flows,
                'total_flows': len(sorted_flows)
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    @task
    async def generate_aws_recommendations(self, expensive_resources: List[Dict], flow_analysis: Dict) -> List[Dict]:
        """Generate AWS best practice recommendations based on analysis"""
        recommendations = []
        
        for resource in expensive_resources:
            cost = resource.get('lineItem/blendedCost', 0)
            service = resource.get('product/serviceName', '')
            region = resource.get('product/region', '')
            resource_id = resource.get('lineItem/resourceId', '')
            
            if cost > 50:  # Threshold for high-cost resources
                if 'EC2' in service:
                    recommendations.append({
                        'resource_id': resource_id,
                        'service': service,
                        'cost': cost,
                        'type': 'EC2 Data Transfer Optimization',
                        'priority': 'High' if cost > 200 else 'Medium',
                        'recommendation': 'Implement VPC endpoints to reduce NAT gateway data transfer charges',
                        'implementation': 'Create VPC endpoints for frequently accessed AWS services',
                        'aws_documentation': 'https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html',
                        'estimated_savings': f'Up to 50% reduction in data transfer costs'
                    })
                
                elif 'S3' in service:
                    recommendations.append({
                        'resource_id': resource_id,
                        'service': service,
                        'cost': cost,
                        'type': 'S3 Data Transfer Optimization',
                        'priority': 'High' if cost > 100 else 'Medium',
                        'recommendation': 'Use CloudFront CDN or S3 Transfer Acceleration',
                        'implementation': 'Configure CloudFront distribution for frequently accessed objects',
                        'aws_documentation': 'https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html',
                        'estimated_savings': f'Up to 60% reduction in data transfer costs'
                    })
                
                elif 'RDS' in service:
                    recommendations.append({
                        'resource_id': resource_id,
                        'service': service,
                        'cost': cost,
                        'type': 'RDS Data Transfer Optimization',
                        'priority': 'Medium',
                        'recommendation': 'Optimize database queries and implement read replicas in same AZ',
                        'implementation': 'Create read replicas closer to application servers',
                        'aws_documentation': 'https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html',
                        'estimated_savings': f'Up to 40% reduction in cross-AZ charges'
                    })
        
        # Add flow-based recommendations
        if flow_analysis.get('status') == 'success':
            flows = flow_analysis.get('flows', [])
            if flows:
                high_traffic_flows = [f for f in flows if f.get('total_bytes', 0) > 500000000]  # >500MB
                
                if high_traffic_flows:
                    recommendations.append({
                        'resource_id': 'Network Traffic Pattern',
                        'service': 'VPC',
                        'cost': 'Variable',
                        'type': 'Network Architecture Optimization',
                        'priority': 'High',
                        'recommendation': 'Optimize data locality and reduce cross-AZ/cross-region traffic',
                        'implementation': 'Review application architecture for data locality patterns',
                        'aws_documentation': 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/networking.html',
                        'estimated_savings': 'Up to 70% reduction in inter-AZ charges'
                    })
        
        return recommendations

    @task
    async def run_complete_analysis(self, cur_bucket: str, cur_prefix: str, target_month: str, vpc_logs_bucket: str, vpc_logs_prefix: str = "vpc-flow-logs/", top_n: int = 10) -> Dict[str, Any]:
        """Execute complete DTO cost analysis workflow for specific month"""
        
        # Step 1: Get expensive DTO resources from CUR for target month
        expensive_resources = await self.analyze_expensive_dto_resources(cur_bucket, cur_prefix, target_month, top_n)
        
        if not expensive_resources:
            return {
                'status': 'no_data',
                'message': f'No expensive DTO resources found in CUR data for {target_month}',
                'recommendations': []
            }
        
        # Step 2: Correlate with VPC flow logs
        resource_ids = [r.get('lineItem/resourceId', '') for r in expensive_resources if r.get('lineItem/resourceId')]
        flow_analysis = await self.correlate_vpc_flow_logs(resource_ids, vpc_logs_bucket, vpc_logs_prefix)
        
        # Step 3: Generate recommendations
        recommendations = await self.generate_aws_recommendations(expensive_resources, flow_analysis)
        
        # Step 4: Compile results
        total_dto_cost = sum(r.get('lineItem/blendedCost', 0) for r in expensive_resources)
        
        return {
            'status': 'success',
            'analysis_summary': {
                'target_month': target_month,
                'total_dto_cost': total_dto_cost,
                'resources_analyzed': len(expensive_resources),
                'flow_logs_status': flow_analysis.get('status'),
                'recommendations_count': len(recommendations)
            },
            'expensive_resources': expensive_resources,
            'flow_analysis': flow_analysis,
            'recommendations': recommendations
        }

# Usage example
async def main():
    agent = DTOCostAnalysisAgent()
    
    result = await agent.run_complete_analysis(
        cur_bucket="my-billing-bucket",
        cur_prefix="cur-reports/",
        target_month="2024-01",
        vpc_logs_bucket="my-vpc-logs-bucket",
        vpc_logs_prefix="vpc-flow-logs/",
        top_n=10
    )
    
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())