import 'package:flutter/foundation.dart';

/// 포그라운드 서비스 관리 (웨이크워드 상시 대기)
/// 현재 버전은 no-op 구현입니다. 향후 flutter_foreground_task 재통합 예정.
class LouisForegroundService {
  LouisForegroundService._();
  static final instance = LouisForegroundService._();

  bool _running = false;
  bool get isRunning => _running;

  Future<void> initialize() async {
    debugPrint('[ForegroundService] 초기화 (비활성화 상태)');
  }

  Future<bool> start() async {
    debugPrint('[ForegroundService] 시작 요청 (비활성화 상태)');
    _running = false;
    return false;
  }

  Future<void> stop() async {
    _running = false;
  }

  Future<void> updateNotification(String text) async {}
}
