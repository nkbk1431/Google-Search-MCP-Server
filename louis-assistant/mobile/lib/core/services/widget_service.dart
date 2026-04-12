import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

/// 홈 화면 위젯과 Flutter 앱 간의 데이터 동기화 서비스
///
/// Android 위젯(LouisWidget)이 SharedPreferences에서 읽는 데이터를
/// Flutter 쪽에서 업데이트합니다.
class WidgetService {
  static const _channel = MethodChannel('com.yourname.louis/intents');

  static WidgetService? _instance;
  factory WidgetService() => _instance ??= WidgetService._();
  WidgetService._();

  /// 다음 리마인더 텍스트를 위젯에 반영합니다.
  /// [text]가 null이면 "예정된 리마인더가 없어요" 로 초기화합니다.
  Future<void> updateNextReminder(String? text) async {
    try {
      await _channel.invokeMethod('updateWidgetReminder', {
        'text': text ?? '예정된 리마인더가 없어요',
      });
    } on PlatformException catch (e) {
      debugPrint('[Widget] 리마인더 업데이트 실패: ${e.message}');
    }
  }

  /// 위젯을 강제로 새로고침합니다.
  Future<void> forceRefresh() async {
    try {
      await _channel.invokeMethod('refreshWidget');
    } on PlatformException catch (e) {
      debugPrint('[Widget] 위젯 새로고침 실패: ${e.message}');
    }
  }
}
