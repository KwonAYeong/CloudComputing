// ========== API 호출 함수들 ==========

// 파일 목록 조회
async function fetchFileList(userId) {
    const response = await fetch(`${CONFIG.API_BASE_URL}/list?user_id=${userId}`);
    if (!response.ok) {
        throw new Error('파일 목록 조회 실패');
    }
    return await response.json();
}

// 업로드 URL 요청
async function requestUploadUrl(userId, filename) {
    const response = await fetch(`${CONFIG.API_BASE_URL}/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            filename: filename
        })
    });
    
    if (!response.ok) {
        throw new Error('업로드 URL 발급 실패');
    }
    
    return await response.json();
}

// S3에 파일 업로드
async function uploadFileToS3(uploadUrl, file) {
    const response = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: {
            'Content-Type': 'application/pdf'
        }
    });
    
    if (!response.ok) {
        throw new Error('파일 업로드 실패');
    }
}

// 요약 상태 조회
async function fetchSummaryStatus(userId, fileId) {
    const response = await fetch(`${CONFIG.API_BASE_URL}/summary?user_id=${userId}&file_id=${fileId}`);
    if (!response.ok) {
        throw new Error('요약 상태 조회 실패');
    }
    return await response.json();
}

// 질의응답
async function sendChatMessage(userId, fileId, question) {
    const response = await fetch(`${CONFIG.API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            file_id: fileId,
            question: question
        })
    });
    
    if (!response.ok) {
        throw new Error('답변 생성 실패');
    }
    
    return await response.json();
}