import boto3
import json
import uuid
import os
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
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
    order_id = str(uuid.uuid4())

    item = {
        'order_id': order_id,
        'entity_type': 'ORDER',
        'creation_date': now,
        'price': Decimal(str(price)),
        'description': description,
        'last_modified': now
    }

    table.put_item(Item=item)
    item['price'] = float(item['price'])

    return {
        'statusCode': 201,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(item)
    }