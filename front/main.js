// ========== 메인 초기화 ==========

// 페이지 로드 시 실행
window.addEventListener("DOMContentLoaded", () => {
  // User ID 가져오기
  const userId = getUserId();
  console.log("User ID:", userId);

  // FileManager 초기화
  FileManager.init(userId);

  // ChatManager 초기화
  ChatManager.init(userId);

  console.log("앱 초기화 완료");
});
