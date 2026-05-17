import boto3
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def lambda_handler(event, context):
    order_id = event['pathParameters']['order_id']
    body = json.loads(event.get('body', '{}'))
    price = body.get('price')
    description = body.get('description')

    if price is None or description is None:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'price and description are required'})
        }

    now = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET price = :p, description = :d, last_modified = :lm',
            ExpressionAttributeValues={
                ':p': Decimal(str(price)),
                ':d': description,
                ':lm': now
            },
            ConditionExpression='attribute_exists(order_id)',  
            ReturnValues='ALL_NEW'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Order not found'})
            }
        raise

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(response['Attributes'], cls=DecimalEncoder)
    }