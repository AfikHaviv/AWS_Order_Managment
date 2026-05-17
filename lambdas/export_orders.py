import boto3
import json
import os
import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
s3 = boto3.client('s3')
BUCKET = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    # Step 1: Read all orders from DynamoDB
    response = table.query(
        IndexName='creation_date_index',
        KeyConditionExpression=Key('entity_type').eq('ORDER')
    )
    orders = response['Items']

    # Step 2: Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Description', 'Price', 'Creation Date', 'Last Modified'])
    for o in orders:
        writer.writerow([
            o.get('order_id', ''),
            o.get('description', ''),
            str(o.get('price', '')),
            o.get('creation_date', ''),
            o.get('last_modified', '')
        ])

    # Step 3: Save to S3
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    key = f"exports/orders_{timestamp}.csv"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=output.getvalue().encode('utf-8'),
        ContentType='text/csv'
    )

    # Step 4: Return pre-signed URL
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': key},
        ExpiresIn=3600
    )

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'csv_url': url,
            'total_orders': len(orders),
            'filename': f'orders_{timestamp}.csv'
        })
    }