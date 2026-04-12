import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

/// 로컬 푸시 알림 서비스
/// 리마인더 알림을 기기에 표시합니다.
class NotificationService {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  static const _androidChannel = AndroidNotificationDetails(
    'louis_reminders',
    '루이스 리마인더',
    channelDescription: '루이스 개인비서 알림',
    importance: Importance.high,
    priority: Priority.high,
    playSound: true,
  );
  static const _notificationDetails = NotificationDetails(
    android: _androidChannel,
    iOS: DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    ),
  );

  static Future<void> initialize() async {
    if (_initialized) return;

    // 타임존 데이터 초기화
    tz_data.initializeTimeZones();
    try {
      final localTz = await FlutterTimezone.getLocalTimezone();
      tz.setLocalLocation(tz.getLocation(localTz));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('Asia/Seoul'));
    }

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    await _plugin.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: (details) {
        // 알림 탭 시 앱이 foreground로 전환됨 (딥링크 추가 가능)
        debugPrint('[NotificationService] 알림 탭: ${details.payload}');
      },
    );

    // Android 13+ 알림 권한 요청
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    // Android 정확한 알람 권한 요청 (SCHEDULE_EXACT_ALARM)
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestExactAlarmsPermission();

    _initialized = true;
  }

  /// 즉시 알림 표시
  static Future<void> show({
    required int id,
    required String title,
    required String body,
    String? payload,
  }) async {
    await initialize();
    await _plugin.show(id, title, body, _notificationDetails, payload: payload);
  }

  /// 예약 알림 (특정 시각)
  ///
  /// [scheduledAt]이 현재 시각보다 과거이면 즉시 표시합니다.
  static Future<void> schedule({
    required int id,
    required String title,
    required String body,
    required DateTime scheduledAt,
    String? payload,
  }) async {
    await initialize();

    final scheduledTz = tz.TZDateTime.from(scheduledAt, tz.local);
    final now = tz.TZDateTime.now(tz.local);

    // 이미 지난 시각이면 즉시 표시
    if (scheduledTz.isBefore(now)) {
      await show(id: id, title: title, body: body, payload: payload);
      return;
    }

    await _plugin.zonedSchedule(
      id,
      title,
      body,
      scheduledTz,
      _notificationDetails,
      payload: payload,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
    );
  }

  /// 특정 ID의 알림 취소
  static Future<void> cancel(int id) async {
    await _plugin.cancel(id);
  }

  /// 모든 예약/표시 알림 취소
  static Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }
}
