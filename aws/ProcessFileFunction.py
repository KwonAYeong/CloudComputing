import json
import boto3
import urllib.parse
import uuid
import datetime
import io
import traceback
from pypdf import PdfReader

# --- 설정 ---
TABLE_NAME = "DocumentTable"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
# -----------

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client(service_name='bedrock-runtime')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("🚀 Lambda 시작")
    
    # 실패 시 기록을 위한 변수 초기화
    user_id = "unknown"
    file_id = "unknown"
    display_filename = "알수없음.pdf"

    try:
        # 1. S3 이벤트에서 파일 ID 가져오기
        bucket = event['Records'][0]['s3']['bucket']['name']
        raw_key = event['Records'][0]['s3']['object']['key']
        
        file_id = urllib.parse.unquote_plus(raw_key)
        
        print(f"📂 원본 Key: {raw_key}")
        print(f"📂 복구된 File ID: {file_id}")

        # 2. 파일명 복구 (ID 분해)
        try:
            parts = file_id.split('_____')
            if len(parts) >= 3:
                user_id = parts[0]
                encoded_name = parts[2]
                display_filename = urllib.parse.unquote(encoded_name)
            else:
                user_id = parts[0] if len(parts) > 0 else "unknown"
                display_filename = file_id
        except Exception as e:
            print(f"이름 파싱 경고: {e}")
            display_filename = file_id

        print(f"화면에 표시할 이름: {display_filename}")

        # 3. 파일 다운로드 & 텍스트 추출
        file_obj = s3.get_object(Bucket=bucket, Key=file_id) 
        file_content = file_obj['Body'].read()
        
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        extracted_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: extracted_text += t + "\n"
        
        if not extracted_text.strip():
            raise Exception("텍스트를 추출할 수 없습니다.")

        # 4. AI 요약
        prompt = f"Human: 다음 텍스트 요약해줘.\n<text>{extracted_text[:15000]}</text>\nAssistant:"
        body = json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]})
        
        ai_response = bedrock.invoke_model(modelId=MODEL_ID, body=body)
        summary = json.loads(ai_response.get('body').read())['content'][0]['text']

        # 5. DB 저장 
        table.put_item(
            Item={
                'user_id': user_id,
                'file_id': file_id,           
                'filename': display_filename, 
                'summary': summary,
                'upload_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'COMPLETED'
            }
        )
        return {'statusCode': 200, 'body': json.dumps('Success')}

    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        traceback.print_exc()
        
        if user_id != "unknown":
            try:
                table.put_item(
                    Item={
                        'user_id': user_id,
                        'file_id': file_id,
                        'filename': display_filename,
                        'status': 'FAILED',
                        'summary': f"처리 중 오류: {str(e)}",
                        'upload_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
            except:
                pass
                
        return {'statusCode': 500, 'body': json.dumps(f"Error: {str(e)}")}