// ========== User ID 관리 ==========
function getUserId() {
    let id = localStorage.getItem(CONFIG.LOCAL_STORAGE_KEY);
    if (!id) {
        id = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem(CONFIG.LOCAL_STORAGE_KEY, id);
    }
    return id;
}

// ========== DOM 헬퍼 함수 ==========
function removeEmptyState() {
    const empty = document.getElementById('emptyState');
    if (empty) {
        empty.remove();
    }
}

function addMessage(text, type) {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex ${type === 'user' ? 'justify-end' : 'justify-start'} mb-4`;
    
    const bubble = document.createElement('div');
    bubble.className = `max-w-[70%] px-4 py-3 rounded-lg whitespace-pre-wrap ${
        type === 'user' 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-800 text-gray-200'
    }`;
    bubble.textContent = text;
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingMessage() {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.id = 'loadingMessage';
    messageDiv.className = 'flex justify-start mb-4';
    
    const bubble = document.createElement('div');
    bubble.className = 'px-4 py-3 rounded-lg bg-gray-800';
    bubble.innerHTML = `
        <div class="flex items-center gap-2">
            <div class="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
            <span class="text-gray-400">생성 중...</span>
        </div>
    `;
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoadingMessage() {
    const loading = document.getElementById('loadingMessage');
    if (loading) loading.remove();
}

function showError(message) {
    addMessage(`⚠️ ${message}`, 'assistant');
}