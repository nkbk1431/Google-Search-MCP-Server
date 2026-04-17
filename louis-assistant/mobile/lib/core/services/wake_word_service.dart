import 'package:flutter/foundation.dart';

/// 웨이크워드 감지 서비스 (버튼 트리거 방식)
///
/// 현재는 마이크 버튼으로 활성화합니다.
/// 향후 온디바이스 웨이크워드가 필요하면 sherpa_onnx 패키지 연동 예정.
class WakeWordService extends ChangeNotifier {
  bool _isRunning = false;
  VoidCallback? _onWakeWord;

  bool get isRunning => _isRunning;

  Future<void> start({required VoidCallback onWakeWord}) async {
    _onWakeWord = onWakeWord;
    _isRunning = true;
    notifyListeners();
    debugPrint('[WakeWord] 버튼 트리거 모드 시작');
  }

  /// 마이크 버튼 또는 외부 이벤트에서 호출
  void trigger() {
    _onWakeWord?.call();
  }

  Future<void> pause() async {
    _isRunning = false;
    notifyListeners();
  }

  Future<void> resume() async {
    _isRunning = true;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    _isRunning = false;
    _onWakeWord = null;
    super.dispose();
  }
}
