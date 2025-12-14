import json
import boto3
import uuid
import urllib.parse 
from boto3.dynamodb.conditions import Key

# --- 설정 ---
BUCKET_NAME = "hansei-project-file-upload"
TABLE_NAME = "DocumentTable"
# -----------

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    try:
        # 1. 업로드 URL 발급 (파일명 포함해서 ID 생성)
        if path == '/upload-url' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            original_filename = body.get('filename') 
            user_id = body.get('user_id')
            
            safe_filename = urllib.parse.quote(original_filename)
            
            safe_file_id = f"{user_id}_____{uuid.uuid4()}_____{safe_filename}"
            
            upload_url = s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': BUCKET_NAME, 
                    'Key': safe_file_id, 
                    'ContentType': 'application/pdf'
                },
                ExpiresIn=3600
            )
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'upload_url': upload_url, 'file_id': safe_file_id})
            }

        # 2. 파일 목록 조회 
        elif path == '/list' and http_method == 'GET':
            user_id = event.get('queryStringParameters', {}).get('user_id')
            if not user_id: return {'statusCode': 400, 'headers': headers, 'body': json.dumps('id required')}
            response = table.query(KeyConditionExpression=Key('user_id').eq(user_id))
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'files': response.get('Items', [])})}

        # 3. 요약 상태 조회 
        elif path == '/summary' and http_method == 'GET':
            params = event.get('queryStringParameters', {})
            user_id = params.get('user_id')
            file_id = params.get('file_id')
            
            response = table.get_item(Key={'user_id': user_id, 'file_id': file_id})
            item = response.get('Item', {})
            
            return {
                'statusCode': 200, 
                'headers': headers, 
                'body': json.dumps({
                    'status': item.get('status', 'PROCESSING'), 
                    'summary_text': item.get('summary', ''),
                    'chat_history': item.get('chat_history', [])
                })
            }
            
        else: return {'statusCode': 404, 'headers': headers, 'body': json.dumps('Not Found')}

    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps(f"Error: {str(e)}")}