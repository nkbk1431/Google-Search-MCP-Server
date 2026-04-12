import 'package:flutter/foundation.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';

/// 포그라운드 서비스 관리
/// 웨이크워드 상시 대기를 위해 Android 포그라운드 서비스를 유지합니다.
/// iOS는 Background Audio로 대체됩니다.
class LouisForegroundService {
  LouisForegroundService._();
  static final instance = LouisForegroundService._();

  bool _running = false;
  bool get isRunning => _running;

  /// 포그라운드 서비스를 초기화합니다.
  Future<void> initialize() async {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'louis_wake_word',
        channelName: '루이스 대기 중',
        channelDescription: '"루이스"라고 부르면 즉시 응답합니다.',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        iconData: const NotificationIconData(
          resType: ResourceType.mipmap,
          resPrefix: ResourcePrefix.ic,
          name: 'launcher',
        ),
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: true,
        playSound: false,
      ),
      foregroundTaskOptions: const ForegroundTaskOptions(
        interval: 5000,
        isOnceEvent: false,
        autoRunOnBoot: true,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  /// 포그라운드 서비스를 시작합니다.
  Future<bool> start() async {
    if (_running) return true;

    final isGranted = await _requestRequiredPermissions();
    if (!isGranted) {
      debugPrint('[포그라운드 서비스] 권한 없음');
      return false;
    }

    final result = await FlutterForegroundTask.startService(
      notificationTitle: '루이스 대기 중',
      notificationText: '"루이스"라고 불러주세요',
      callback: _foregroundTaskCallback,
    );

    _running = result == ServiceRequestResult.success;
    return _running;
  }

  /// 포그라운드 서비스를 중지합니다.
  Future<void> stop() async {
    await FlutterForegroundTask.stopService();
    _running = false;
  }

  /// 알림 텍스트를 업데이트합니다.
  Future<void> updateNotification(String text) async {
    if (!_running) return;
    await FlutterForegroundTask.updateService(
      notificationTitle: '루이스',
      notificationText: text,
    );
  }

  Future<bool> _requestRequiredPermissions() async {
    // Android 13+ 알림 권한
    if (!await FlutterForegroundTask.isIgnoringBatteryOptimizations) {
      await FlutterForegroundTask.requestIgnoreBatteryOptimization();
    }
    return true;
  }
}

/// 포그라운드 태스크 콜백 (별도 Isolate에서 실행)
@pragma('vm:entry-point')
void _foregroundTaskCallback() {
  FlutterForegroundTask.setTaskHandler(LouisTaskHandler());
}

class LouisTaskHandler extends TaskHandler {
  @override
  Future<void> onStart(DateTime timestamp, SendPort? sendPort) async {
    debugPrint('[ForegroundTask] 시작: $timestamp');
  }

  @override
  Future<void> onRepeatEvent(DateTime timestamp, SendPort? sendPort) async {
    // 주기적 이벤트: 웨이크워드 감지 상태 확인
    sendPort?.send({'type': 'heartbeat', 'timestamp': timestamp.toIso8601String()});
  }

  @override
  Future<void> onDestroy(DateTime timestamp, SendPort? sendPort) async {
    debugPrint('[ForegroundTask] 종료: $timestamp');
  }

  @override
  void onNotificationPressed() {
    // 알림 탭 시 앱 화면으로 이동
    FlutterForegroundTask.launchApp('/');
  }
}
