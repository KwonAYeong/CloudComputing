import json
import boto3
import urllib.parse
import uuid
import datetime
import io
from pypdf import PdfReader

# --- [설정 구간] ---
TABLE_NAME = "DocumentTable"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
# ------------------

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client(service_name='bedrock-runtime')

def lambda_handler(event, context):
    print("🚀 Lambda 시작 (pypdf - UserID 자동추출 버전)")
    
    try:
        # 1. S3 이벤트에서 파일 정보 가져오기
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        print(f"📂 파일 감지됨: {bucket} / {key}")

        # 파일 이름에서 user_id 추출하기
        # 파일명 예시: user_12345_____uuid.pdf
        try:
            # '_____' 기준으로 쪼개서 앞부분을 가져옴
            user_id = key.split('_____')[0]
            print(f"👤 추출된 사용자 ID: {user_id}")
        except:
            user_id = "unknown_user" # 만약 형식이 다르면 임시 처리
            print("⚠️ 사용자 ID 추출 실패, unknown으로 저장")

        # 2. S3에서 파일 다운로드
        file_obj = s3.get_object(Bucket=bucket, Key=key)
        file_content = file_obj['Body'].read()
        
        # 3. pypdf로 텍스트 추출
        print("🔍 pypdf로 텍스트 읽는 중...")
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
        
        print(f"✅ 추출 완료! 길이: {len(extracted_text)}자")
        
        if len(extracted_text.strip()) == 0:
            raise Exception("텍스트가 없습니다. (이미지 PDF는 못 읽음)")

        # 4. Bedrock에게 요약 요청
        print("🧠 AI 요약 요청 중...")
        prompt = f"""
        Human: 다음 텍스트는 문서의 내용이야. 핵심 내용을 3줄로 요약해줘. 한국어로 답변해.
        
        <text>
        {extracted_text[:15000]} 
        </text>
        
        Assistant:
        """

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })

        ai_response = bedrock.invoke_model(modelId=MODEL_ID, body=body)
        response_body = json.loads(ai_response.get('body').read())
        summary_result = response_body['content'][0]['text']
        
        print(f"🤖 AI 요약 완료: {summary_result}")

        # 5. DynamoDB 저장 (진짜 ID로 저장!)
        print("💾 DB 저장 중...")
        table = dynamodb.Table(TABLE_NAME)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        table.put_item(
            Item={
                'user_id': user_id,          # 추출한 user_id 사용
                'file_id': key,              # 파일명(ID포함)을 그대로 Key로 사용
                'filename': key,
                'summary': summary_result,
                'upload_date': timestamp,
                'status': 'COMPLETED'
            }
        )
        
        return {'statusCode': 200, 'body': json.dumps('Success!')}

    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps(f"Error: {str(e)}")}