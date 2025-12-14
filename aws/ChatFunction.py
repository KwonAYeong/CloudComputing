import json
import boto3
import io
import urllib.parse
from pypdf import PdfReader

# --- [설정 구간] ---
BUCKET_NAME = "hansei-project-file-upload" # 버킷 이름
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
TABLE_NAME = "DocumentTable"
# ------------------

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client(service_name='bedrock-runtime')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("💬 채팅 요청:", json.dumps(event))
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    try:
        if 'body' in event and event['body']:
            body_data = json.loads(event['body'])
        else:
            body_data = event
            
        file_id = body_data.get('file_id') 
        question = body_data.get('question')
        user_id = body_data.get('user_id')
        
        # 여기서 file_id가 곧 S3에 저장된 파일명(UUID.pdf)임
        print(f"질문: {question} / 파일Key: {file_id}")

        if not file_id or not question:
            raise Exception("file_id와 question은 필수입니다.")

        # 1. S3에서 파일 읽기
        file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_id)
        file_content = file_obj['Body'].read()
        
        # 2. PDF 텍스트 추출
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text: extracted_text += text + "\n"
            if len(extracted_text) > 15000: break
                
        # 3. DB에서 이전 대화 기록 가져오기 
        chat_history_text = ""
        if user_id:
            try:
                db_resp = table.get_item(Key={'user_id': user_id, 'file_id': file_id})
                history = db_resp.get('Item', {}).get('chat_history', [])
                # 최근 2개 대화만 참고 
                for h in history[-2:]: 
                    chat_history_text += f"User: {h['question']}\nAI: {h['answer']}\n"
            except:
                pass

        # 4. Bedrock 질문
        prompt = f"""
        Human: 너는 문서 분석 전문가야. 다음 문서를 보고 사용자의 질문에 답해줘.
        
        [문서 내용]
        {extracted_text[:15000]}
        
        [이전 대화]
        {chat_history_text}
        
        User Question: {question}
        
        Assistant:
        """

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response.get('body').read())
        answer = response_body['content'][0]['text']
        
        # 5. 대화 내용 DB에 저장 (History 업데이트)
        if user_id:
            try:
                # 리스트에 append (DynamoDB list_append 기능 사용 불가시 그냥 읽어서 업데이트)
                # 여기선 간단하게 기존 항목 가져와서 업데이트하는 방식 사용
                current_item = table.get_item(Key={'user_id': user_id, 'file_id': file_id}).get('Item', {})
                current_history = current_item.get('chat_history', [])
                current_history.append({'question': question, 'answer': answer, 'timestamp': str(datetime.datetime.now())})
                
                table.update_item(
                    Key={'user_id': user_id, 'file_id': file_id},
                    UpdateExpression="set chat_history = :h",
                    ExpressionAttributeValues={':h': current_history}
                )
            except Exception as db_err:
                print(f"DB 저장 실패(무시): {str(db_err)}")

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'answer': answer})
        }

    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps(f"Error: {str(e)}")
        }