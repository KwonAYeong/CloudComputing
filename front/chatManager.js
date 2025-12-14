// ========== 채팅 관리 ==========

const ChatManager = {
  userId: null,

  // 초기화
  init(userId) {
    this.userId = userId;
    this.setupEventListeners();
  },

  // 이벤트 리스너 설정
  setupEventListeners() {
    const sendBtn = document.getElementById("sendBtn");
    const messageInput = document.getElementById("messageInput");
    const newChatBtn = document.getElementById("newChatBtn");

    sendBtn.addEventListener("click", () => {
      this.sendMessage();
    });

    messageInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.sendMessage();
      }
    });

    newChatBtn.addEventListener("click", () => {
      this.startNewChat();
    });
  },

  // 새 대화 시작
  startNewChat() {
    // FileManager의 상태 초기화
    FileManager.currentFileId = null;
    FileManager.currentFileName = null;

    const fileStatus = document.getElementById("fileStatus");
    fileStatus.classList.add("hidden");

    // 1. 채팅창 다시 잠그기
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");

    messageInput.disabled = true;
    messageInput.placeholder = "파일을 먼저 업로드해주세요...";
    messageInput.value = ""; // 입력하던 거 있으면 지우기
    sendBtn.disabled = true;

    // 2. 업로드 버튼 다시 보여주기
    document.getElementById("uploadBtn").classList.remove("hidden");

    // 채팅창 초기화
    const chatMessages = document.getElementById("chatMessages");
    chatMessages.innerHTML = `
            <div id="emptyState" class="flex flex-col items-center justify-center h-full">
                <svg class="w-20 h-20 text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <h2 class="text-2xl font-semibold text-gray-300 mb-2">문서를 업로드하고 대화를 시작하세요</h2>
                <p class="text-gray-500">PDF 파일을 업로드하면 자동으로 요약해드립니다</p>
            </div>
        `;

    // 사이드바 선택 해제
    FileManager.updateSidebarSelection();
  },

  // 메시지 전송
  async sendMessage() {
    const messageInput = document.getElementById("messageInput");
    const message = messageInput.value.trim();

    if (!message) return;

    // 파일이 선택되지 않았으면
    const currentFileId = FileManager.getCurrentFileId();
    if (!currentFileId) {
      alert("먼저 문서를 업로드하거나 선택해주세요.");
      return;
    }

    removeEmptyState();

    // 사용자 메시지 추가
    addMessage(message, "user");
    messageInput.value = "";

    // 로딩 메시지
    addLoadingMessage();

    try {
      const data = await sendChatMessage(this.userId, currentFileId, message);

      removeLoadingMessage();
      addMessage(data.answer, "assistant");
    } catch (error) {
      console.error("메시지 전송 오류:", error);
      removeLoadingMessage();
      showError("답변을 생성하는 중 오류가 발생했습니다.");
    }
  },
};
