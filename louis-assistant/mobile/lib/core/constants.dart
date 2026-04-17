/// 루이스 앱 상수 정의
class AppConstants {
  AppConstants._();

  // API 설정
  // 빌드 시 --dart-define=BASE_URL=http://192.168.x.x:8000 으로 주입 가능
  // 미지정 시 설정 화면에서 직접 입력 (권장)
  static const String apiBaseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: 'http://10.0.2.2:8000', // Android 에뮬레이터 기본값 (localhost)
  );
  static const String apiVersion = 'v1';

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
