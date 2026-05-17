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

    # Find the SubscriptionArn by email
    response = sns.list_subscriptions_by_topic(
        TopicArn=os.environ['SNS_TOPIC_ARN']
    )

    sub_arn = None
    for sub in response['Subscriptions']:
        if sub['Endpoint'] == email:
            sub_arn = sub['SubscriptionArn']
            break

    if not sub_arn:
        return {
            'statusCode': 404,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Email not subscribed'})
        }

    # Cannot cancel a subscription that has not been confirmed yet
    if sub_arn == 'PendingConfirmation':
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Subscription not confirmed yet. Check your email.'})
        }

    sns.unsubscribe(SubscriptionArn=sub_arn)

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'message': 'Unsubscribed successfully'})
    }