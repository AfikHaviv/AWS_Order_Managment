import boto3
import json
import os
from datetime import datetime, timezone

s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    for record in event['Records']:
        # SQS wraps the SNS message inside 'body'
        sqs_body = json.loads(record['body'])

        # SNS message is inside 'Message' key
        if 'Message' in sqs_body:
            message_str = sqs_body['Message']
        else:
            message_str = record['body']

        order = json.loads(message_str)

        order_id  = order.get('order_id', 'unknown')
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        txt_content = f"""Order ID:       {order.get('order_id', 'N/A')}
Description:    {order.get('description', 'N/A')}
Price:          {order.get('price', 'N/A')}
Creation Date:  {order.get('creation_date', 'N/A')}
Deleted At:     {datetime.now(timezone.utc).isoformat()}
"""
        key = f"backups/{order_id}_{timestamp}.txt"
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=txt_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"Backup saved: {key}")

    return {'statusCode': 200}