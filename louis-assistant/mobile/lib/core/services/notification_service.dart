import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// 로컬 푸시 알림 서비스
/// 리마인더 알림을 기기에 표시합니다.
class NotificationService {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  static Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    await _plugin.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: (details) {
        // TODO: 알림 탭 시 처리
      },
    );
    _initialized = true;
  }

  /// 즉시 알림 표시
  static Future<void> show({
    required int id,
    required String title,
    required String body,
  }) async {
    await initialize();
    await _plugin.show(
      id,
      title,
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'louis_reminders',
          '루이스 리마인더',
          channelDescription: '루이스 개인비서 알림',
          importance: Importance.high,
          priority: Priority.high,
        ),
        iOS: DarwinNotificationDetails(),
      ),
    );
  }

  /// 예약 알림 (특정 시각)
  static Future<void> schedule({
    required int id,
    required String title,
    required String body,
    required DateTime scheduledAt,
  }) async {
    await initialize();
    // TODO: AndroidFlutterLocalNotificationsPlugin.requestExactAlarmsPermission()
    // flutter_local_notifications의 zonedSchedule 사용 권장
  }
}
