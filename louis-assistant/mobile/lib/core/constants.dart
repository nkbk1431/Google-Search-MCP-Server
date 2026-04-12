/// 루이스 앱 상수 정의
class AppConstants {
  AppConstants._();

  // API 설정 (실제 URL로 교체)
  static const String apiBaseUrl = 'https://your-cloudrun-url.run.app';
  static const String apiVersion = 'v1';

  // 웨이크워드 파일 경로 (assets/)
  static const String wakeWordModelPath = 'assets/wake_words/porcupine_params_ko.pv';
  static const String wakeWordKeywordPath = 'assets/wake_words/louis_ko.ppn';

  // 음성 설정
  static const String sttLocale = 'ko_KR';
  static const double ttsRate = 0.5;      // 0.0 ~ 1.0
  static const double ttsPitch = 1.0;
  static const double ttsVolume = 1.0;

  // 대화 설정
  static const int maxConversationTurns = 20;  // 이 이상이면 요약
  static const int apiTimeoutSeconds = 30;
  static const int sttTimeoutSeconds = 8;

  // 로컬 저장소 키
  static const String keyAccessToken = 'access_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUsername = 'username';
  static const String keySessionId = 'session_id';
  static const String keyOnboardingDone = 'onboarding_done';

  // 앱 정보
  static const String appName = '루이스';
  static const String appVersion = '1.0.0';
}
