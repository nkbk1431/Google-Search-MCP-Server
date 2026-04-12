import 'package:flutter/foundation.dart';
import 'package:porcupine_flutter/porcupine_flutter.dart';
import '../constants.dart';

/// 웨이크워드 감지 서비스
/// Picovoice Porcupine 기반 온디바이스 처리
class WakeWordService extends ChangeNotifier {
  PorcupineManager? _manager;
  bool _isRunning = false;
  String? _picovoiceAccessKey;

  bool get isRunning => _isRunning;

  /// 웨이크워드 감지를 초기화하고 시작합니다.
  /// [onWakeWord]: 웨이크워드 감지 시 호출될 콜백
  Future<void> start({
    required String accessKey,
    required VoidCallback onWakeWord,
  }) async {
    _picovoiceAccessKey = accessKey;

    try {
      _manager = await PorcupineManager.fromKeywordPaths(
        accessKey,
        [AppConstants.wakeWordKeywordPath],
        (keywordIndex) {
          if (keywordIndex == 0) {
            debugPrint('[웨이크워드] 루이스 감지!');
            onWakeWord();
          }
        },
        modelPath: AppConstants.wakeWordModelPath,
        errorCallback: (error) {
          debugPrint('[웨이크워드 오류] $error');
        },
      );

      await _manager!.start();
      _isRunning = true;
      notifyListeners();
      debugPrint('[웨이크워드] 대기 시작');
    } catch (e) {
      debugPrint('[웨이크워드] 초기화 실패: $e');
      _isRunning = false;
    }
  }

  /// 웨이크워드 감지를 일시 중지합니다. (음성 입력 중)
  Future<void> pause() async {
    await _manager?.stop();
    _isRunning = false;
    notifyListeners();
  }

  /// 웨이크워드 감지를 재개합니다.
  Future<void> resume() async {
    await _manager?.start();
    _isRunning = true;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    await _manager?.delete();
    _manager = null;
    _isRunning = false;
    super.dispose();
  }
}
