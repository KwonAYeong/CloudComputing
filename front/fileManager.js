// ========== 파일 관리 ==========

const FileManager = {
  currentFileId: null,
  currentFileName: null,
  pollingInterval: null,
  userId: null,

  // 초기화
  init(userId) {
    this.userId = userId;
    this.setupEventListeners();
    this.loadFileList();
  },

  // 이벤트 리스너 설정
  setupEventListeners() {
    const uploadBtn = document.getElementById("uploadBtn");
    const fileInput = document.getElementById("fileInput");

    uploadBtn.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });
  },

  // 파일 목록 불러오기
  async loadFileList() {
    const chatList = document.getElementById("chatList");

    try {
      const data = await fetchFileList(this.userId);

      chatList.innerHTML = "";

      if (data.files && data.files.length > 0) {
        data.files.sort((a, b) => {
          return new Date(b.upload_date) - new Date(a.upload_date);
        });
        data.files.forEach((file) => {
          this.addFileToList(file);
        });
      } else {
        chatList.innerHTML =
          '<div class="text-center text-gray-500 text-sm py-4">업로드한 문서가 없습니다</div>';
      }
    } catch (error) {
      console.error("파일 목록 불러오기 오류:", error);
      chatList.innerHTML =
        '<div class="text-center text-gray-500 text-sm py-4">목록을 불러올 수 없습니다</div>';
    }
  },

  // 파일을 리스트에 추가
  addFileToList(file) {
    const chatList = document.getElementById("chatList");
    const fileItem = document.createElement("div");

    fileItem.className = `px-3 py-2 rounded-lg cursor-pointer transition-colors ${
      file.file_id === this.currentFileId
        ? "bg-gray-800 text-white"
        : "text-gray-400 hover:bg-gray-900"
    }`;

    const title =
      file.filename.length > 25
        ? file.filename.substring(0, 25) + "..."
        : file.filename;

    const statusIcon =
      file.status === "COMPLETED"
        ? "✓"
        : file.status === "PROCESSING"
        ? "⏳"
        : "⚠";

    fileItem.innerHTML = `
            <div class="flex items-center justify-between">
                <span>${title}</span>
                <span class="text-xs">${statusIcon}</span>
            </div>
        `;

    fileItem.addEventListener("click", () => {
      this.loadChat(file.file_id, file.filename);
    });

    chatList.appendChild(fileItem);
  },

  // 파일 업로드 처리
  async handleFileUpload(file) {
    try {
      removeEmptyState();

      // 사용자 메시지
      addMessage(`${file.name} 파일을 업로드했습니다.`, "user");
      addLoadingMessage();

      // 1. Presigned URL 요청
      const { upload_url, file_id } = await requestUploadUrl(
        this.userId,
        file.name
      );

      this.currentFileId = file_id;
      this.currentFileName = file.name;

      // 2. S3에 업로드
      await uploadFileToS3(upload_url, file);

      // 파일 상태 표시
      const fileStatus = document.getElementById("fileStatus");
      const fileStatusText = document.getElementById("fileStatusText");
      fileStatus.classList.remove("hidden");
      fileStatusText.textContent = `📄 ${file.name}`;

      removeLoadingMessage();
      addMessage("파일이 업로드되었습니다. 요약을 생성하는 중...", "assistant");

      const messageInput = document.getElementById("messageInput");
      const sendBtn = document.getElementById("sendBtn");

      messageInput.disabled = false;
      messageInput.placeholder = "메시지를 입력하세요..."; // 안내 문구 변경
      messageInput.classList.remove("cursor-not-allowed"); // 마우스 커서도 정상으로
      sendBtn.disabled = false;
      sendBtn.classList.remove("cursor-not-allowed");

      // 2.5 업로드 버튼 숨기기 (중복 방지)
      document.getElementById("uploadBtn").classList.add("hidden");
      // 3. 폴링 시작
      this.startPolling(file_id);

      // 파일 목록 새로고침
      await this.loadFileList();
    } catch (error) {
      console.error("파일 업로드 오류:", error);
      removeLoadingMessage();
      showError("파일 업로드 중 오류가 발생했습니다. 다시 시도해주세요.");
    }
  },

  // 폴링: 요약 완료 확인
  startPolling(fileId) {
    let attempts = 0;

    this.pollingInterval = setInterval(async () => {
      attempts++;

      try {
        const data = await fetchSummaryStatus(this.userId, fileId);

        if (data.status === "COMPLETED") {
          clearInterval(this.pollingInterval);
          addMessage(
            data.summary_text || "요약이 완료되었습니다.",
            "assistant"
          );
          await this.loadFileList();
        } else if (data.status === "FAILED") {
          clearInterval(this.pollingInterval);
          showError("문서 처리 중 오류가 발생했습니다.");
        } else if (attempts >= CONFIG.MAX_POLLING_ATTEMPTS) {
          clearInterval(this.pollingInterval);
          showError("처리 시간이 초과되었습니다. 나중에 다시 확인해주세요.");
        }
      } catch (error) {
        console.error("폴링 오류:", error);
        if (attempts >= CONFIG.MAX_POLLING_ATTEMPTS) {
          clearInterval(this.pollingInterval);
          showError("상태 확인 중 오류가 발생했습니다.");
        }
      }
    }, CONFIG.POLLING_INTERVAL);
  },

  // 대화 불러오기
  async loadChat(fileId, filename) {
    this.currentFileId = fileId;
    this.currentFileName = filename;

    // 1. 채팅창 잠금 해제
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");

    messageInput.disabled = false;
    messageInput.placeholder = "메시지를 입력하세요...";
    messageInput.classList.remove("cursor-not-allowed");
    sendBtn.disabled = false;
    sendBtn.classList.remove("cursor-not-allowed");

    // 🙈 2. 업로드 버튼 숨기기
    document.getElementById("uploadBtn").classList.add("hidden");

    // 1. 사이드바 UI 업데이트 (선택된 파일 강조)
    this.updateSidebarSelection();

    // 2. 채팅창 청소 (기존 대화 지우기)
    const chatMessages = document.getElementById("chatMessages");
    chatMessages.innerHTML = "";
    removeEmptyState(); // 초기 안내 문구 제거

    // 3. 로딩 메시지 띄우기
    addMessage(`📂 ${filename} 내용을 불러오는 중입니다...`, "assistant");

    try {
      // ★ 백엔드 통신: 요약본 + 채팅 내역 가져오기
      // (이미 만들어둔 api.js의 fetchSummaryStatus 함수 재활용)
      const data = await fetchSummaryStatus(this.userId, fileId);

      // 로딩 메시지 지우고 시작
      chatMessages.innerHTML = "";
      addMessage(`✅ ${filename} 파일을 선택했습니다.`, "assistant");

      // [Step 1] 요약문이 있으면 먼저 보여주기
      // (백엔드가 summary_text 라는 이름으로 주기로 했음)
      if (data.summary_text) {
        addMessage(`[📝 AI 요약]\n${data.summary_text}`, "assistant");
      }

      // [Step 2] 채팅 내역(History) 복구하기 (여기가 핵심!)
      // 백엔드가 chat_history 라는 배열을 준다고 가정
      if (data.chat_history && Array.isArray(data.chat_history)) {
        data.chat_history.forEach((chat) => {
          // 백엔드가 { "question": "...", "answer": "..." } 형태로 준다고 가정
          if (chat.question) {
            addMessage(chat.question, "user"); // 내 질문 복구
          }
          if (chat.answer) {
            addMessage(chat.answer, "assistant"); // AI 답변 복구
          }
        });
      }
    } catch (error) {
      console.error("채팅 내역 불러오기 실패:", error);
      // 에러 나도 사용자가 당황하지 않게 메시지 띄워주기
      chatMessages.innerHTML = "";
      addMessage(`⚠️ ${filename}의 정보를 불러오지 못했습니다.`, "assistant");
    }
  },

  // 사이드바 선택 상태 업데이트
  updateSidebarSelection() {
    const chatList = document.getElementById("chatList");
    const items = chatList.querySelectorAll('div[class*="px-3"]');

    items.forEach((item) => {
      if (item.textContent.includes(this.currentFileName)) {
        item.className =
          "px-3 py-2 rounded-lg cursor-pointer transition-colors bg-gray-800 text-white";
      } else {
        item.className =
          "px-3 py-2 rounded-lg cursor-pointer transition-colors text-gray-400 hover:bg-gray-900";
      }
    });
  },

  // Getter
  getCurrentFileId() {
    return this.currentFileId;
  },

  getCurrentFileName() {
    return this.currentFileName;
  },
};
