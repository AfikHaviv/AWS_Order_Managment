import boto3
import json
import os

sns = boto3.client('sns')

def lambda_handler(event, context):
    body = json.loads(event.get('body', '{}'))
    email = body.get('email')

    if not email:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'email is required'})
        }

    sns.subscribe(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Protocol='email',
        Endpoint=email
    )

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'message': 'Subscription pending. Check your email to confirm.'
        })
    }