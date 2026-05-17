import boto3
import json
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
sns = boto3.client('sns')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def lambda_handler(event, context):
    order_id = event['pathParameters']['order_id']

    # Step 1: Read the order before deletion
    response = table.get_item(Key={'order_id': order_id})
    item = response.get('Item')

    if not item:
        return {
            'statusCode': 404,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Order not found'})
        }

    # Step 2: Delete from DynamoDB
    table.delete_item(Key={'order_id': order_id})

    # Step 3: Build a formatted email message
    price = float(item.get('price', 0))
    created = str(item.get('creation_date', 'N/A'))[:19].replace('T', ' ')
    deleted_at = __import__('datetime').datetime.now(
        __import__('datetime').timezone.utc
    ).isoformat()[:19].replace('T', ' ')

    email_message = f"""Hello,

An order has been deleted from the Order Management System.

Order Details
─────────────────────────────
Order ID:     {item.get('order_id')}
Description:  {item.get('description')}
Price:        ${price:.2f}
Created:      {created} UTC
Deleted At:   {deleted_at} UTC
─────────────────────────────

This is an automated notification.
Order Management System — AWS Serverless"""

    # Step 4: Publish to SNS with different format for email and Lambda subscribers
    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject='Order Deleted — Order Management System',
        MessageStructure='json',
        Message=json.dumps({
            'default': json.dumps(item, cls=DecimalEncoder),  # ← backup-order Lambda receives JSON
            'email': email_message                             # ← email subscribers receive formatted message
        })
    )

    # Step 5: Return immediately
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'message': 'Order deleted successfully', 'order_id': order_id})
    }