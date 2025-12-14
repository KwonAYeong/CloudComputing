import json
import boto3
import uuid
import datetime
from boto3.dynamodb.conditions import Key

# --- [설정 구간] ---
BUCKET_NAME = "hansei-project-file-upload"
TABLE_NAME = "DocumentTable"
# ------------------

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("API 요청 도착:", json.dumps(event))
    
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    try:
        # 1. 업로드 URL 발급 요청
        if path == '/upload-url' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            original_filename = body.get('filename') 
            user_id = body.get('user_id') # 프론트에서 보낸 진짜 ID
            
            # 파일명 앞에 유저ID를 붙여서 저장합니다! (구분자: _____)
            ext = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'
            uuid_name = f"{uuid.uuid4()}.{ext}"
            
            # 예: user_123_____abcd-efgh.pdf
            safe_file_id = f"{user_id}_____{uuid_name}"
            
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
                'body': json.dumps({
                    'upload_url': upload_url, 
                    'file_id': safe_file_id 
                })
            }

        # 2. 파일 목록 조회
        elif path == '/list' and http_method == 'GET':
            user_id = event.get('queryStringParameters', {}).get('user_id')
            if not user_id:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps('user_id required')}

            response = table.query(KeyConditionExpression=Key('user_id').eq(user_id))
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'files': response.get('Items', [])})}

        # 3. 요약 상태 조회
        elif path == '/summary' and http_method == 'GET':
            params = event.get('queryStringParameters', {})
            user_id = params.get('user_id')
            file_id = params.get('file_id')
            
            response = table.get_item(Key={'user_id': user_id, 'file_id': file_id})
            item = response.get('Item', {})
            status = item.get('status', 'PROCESSING')
            summary = item.get('summary', '')
            chat_history = item.get('chat_history', [])
            
            return {
                'statusCode': 200, 
                'headers': headers, 
                'body': json.dumps({
                    'status': status, 
                    'summary_text': summary,
                    'chat_history': chat_history
                })
            }
            
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps('Not Found')}

    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps(f"Error: {str(e)}")}