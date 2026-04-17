import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

/// 웨이크워드 감지 서비스
///
/// Android 내장 한국어 STT 엔진으로 연속 인식 → "루이스" 키워드 감지.
/// sherpa-onnx 대신 speech_to_text 패키지를 사용해 추가 모델 없이 동작.
///
/// 동작:
///   1. 한국어 음성 인식을 짧게 반복 실행
///   2. 인식 결과에 웨이크워드(루이스 등)가 포함되면 콜백 호출
///   3. 마이크 권한 없거나 STT 초기화 실패 시 버튼 트리거 모드로 폴백
class WakeWordService extends ChangeNotifier {
  static const _wakeWords = ['루이스', '루이 스', '루이스야', '루이야'];
  static const _listenDuration = Duration(seconds: 4);
  static const _locale = 'ko_KR';

  final stt.SpeechToText _speech = stt.SpeechToText();

  bool _isRunning = false;
  bool _sttActive = false;
  bool _listening = false;
  VoidCallback? _onWakeWord;
  Timer? _loopTimer;

  bool get isRunning => _isRunning;

  /// STT 방식으로 감지 중이면 true, 버튼 트리거면 false
  bool get sttActive => _sttActive;

  Future<void> start({required VoidCallback onWakeWord}) async {
    _onWakeWord = onWakeWord;

    final available = await _speech.initialize(
      onError: (e) => debugPrint('[WakeWord] STT 오류: ${e.errorMsg}'),
      onStatus: (s) => debugPrint('[WakeWord] STT 상태: $s'),
    );

    if (available) {
      _sttActive = true;
      _isRunning = true;
      notifyListeners();
      _startListenLoop();
      debugPrint('[WakeWord] 한국어 STT 웨이크워드 감지 시작');
    } else {
      _sttActive = false;
      _isRunning = true;
      notifyListeners();
      debugPrint('[WakeWord] STT 초기화 실패 → 버튼 트리거 모드');
    }
  }

  /// 마이크 버튼 또는 외부 이벤트로 직접 활성화
  void trigger() => _onWakeWord?.call();

  /// 대화 처리 중 웨이크워드 감지 중단 (마이크 충돌 방지)
  Future<void> pause() async {
    _loopTimer?.cancel();
    _loopTimer = null;
    if (_listening) {
      await _speech.stop();
      _listening = false;
    }
    _isRunning = false;
    notifyListeners();
  }

  /// 대화 완료 후 웨이크워드 감지 재개
  Future<void> resume() async {
    if (_sttActive) _startListenLoop();
    _isRunning = true;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    _loopTimer?.cancel();
    _loopTimer = null;
    if (_listening) {
      await _speech.stop();
      _listening = false;
    }
    _isRunning = false;
    super.dispose();
  }

  // ── 연속 인식 루프 ─────────────────────────────────────────────────

  void _startListenLoop() {
    if (!_sttActive) return;
    _listenOnce();
  }

  Future<void> _listenOnce() async {
    if (!_isRunning || !_sttActive) return;
    if (_listening) return;

    _listening = true;

    await _speech.listen(
      localeId: _locale,
      listenFor: _listenDuration,
      pauseFor: const Duration(seconds: 2),
      partialResults: true,
      onResult: (result) {
        final text = result.recognizedWords.toLowerCase().replaceAll(' ', '');
        if (_containsWakeWord(text)) {
          debugPrint('[WakeWord] 감지: ${result.recognizedWords}');
          _speech.stop();
          _listening = false;
          _onWakeWord?.call();
          // 콜백 호출 후 루프는 resume()에서 재시작
        }
      },
    );

    // listenFor 만료 후 자동 재시작
    _loopTimer = Timer(_listenDuration + const Duration(milliseconds: 500), () {
      _listening = false;
      if (_isRunning && _sttActive) _listenOnce();
    });
  }

  bool _containsWakeWord(String text) {
    return _wakeWords.any((w) => text.contains(w.replaceAll(' ', '')));
  }
}
