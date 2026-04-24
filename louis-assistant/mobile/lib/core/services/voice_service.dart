import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import '../constants.dart';

/// 음성 입출력 서비스
/// STT (음성 → 텍스트) + TTS (텍스트 → 음성)
class VoiceService extends ChangeNotifier {
  final _tts = FlutterTts();
  final _stt = SpeechToText();

  bool _isSpeaking = false;
  bool _isListening = false;
  bool _sttAvailable = false;

  // TTS 속도 (설정에서 변경 가능)
  double _ttsRate = AppConstants.ttsRate;

  // STT 신뢰도 임계값: 이 이하이면 인식 무시
  static const double _confidenceThreshold = 0.4;

  bool get isSpeaking => _isSpeaking;
  bool get isListening => _isListening;
  bool get sttAvailable => _sttAvailable;

  Future<void> initialize() async {
    // 마이크 권한 요청 (Android 런타임 권한)
    final micStatus = await Permission.microphone.request();
    if (!micStatus.isGranted) {
      debugPrint('VoiceService: 마이크 권한 없음 ($micStatus)');
    }

    // TTS 초기화
    await _tts.setLanguage('ko-KR');
    await _tts.setSpeechRate(_ttsRate);
    await _tts.setPitch(AppConstants.ttsPitch);
    await _tts.setVolume(AppConstants.ttsVolume);

    _tts.setStartHandler(() {
      _isSpeaking = true;
      notifyListeners();
    });
    _tts.setCompletionHandler(() {
      _isSpeaking = false;
      notifyListeners();
    });
    _tts.setErrorHandler((msg) {
      _isSpeaking = false;
      debugPrint('TTS 오류: $msg');
      notifyListeners();
    });

    // STT 초기화
    _sttAvailable = await _stt.initialize(
      onError: (err) => debugPrint('STT 오류: $err'),
      onStatus: (status) => debugPrint('STT 상태: $status'),
    );
    debugPrint('VoiceService 초기화 완료. STT 가능: $_sttAvailable');
  }

  /// TTS 속도를 변경합니다 (0.3 ~ 1.0).
  Future<void> setRate(double rate) async {
    _ttsRate = rate.clamp(0.3, 1.0);
    await _tts.setSpeechRate(_ttsRate);
  }

  /// 텍스트를 음성으로 읽어줍니다.
  Future<void> speak(String text) async {
    if (text.trim().isEmpty) return;
    if (_isSpeaking) await stop();
    await _tts.speak(text);
  }

  /// 음성 출력을 멈춥니다.
  Future<void> stop() async {
    await _tts.stop();
    _isSpeaking = false;
    notifyListeners();
  }

  /// 음성을 듣고 텍스트로 변환합니다.
  ///
  /// - [timeoutSeconds]: 전체 인식 타임아웃
  /// - [onPartialResult]: 중간 결과 콜백 (UI 업데이트용)
  /// - 신뢰도 [_confidenceThreshold] 미만 결과는 null 반환
  Future<String?> listen({
    int timeoutSeconds = AppConstants.sttTimeoutSeconds,
    void Function(String partial)? onPartialResult,
  }) async {
    if (!_sttAvailable) {
      debugPrint('STT 불가');
      return null;
    }
    if (_isListening) return null;

    String recognized = '';
    double lastConfidence = 0.0;
    final completer = Completer<String?>();

    _isListening = true;
    notifyListeners();

    await _stt.listen(
      onResult: (SpeechRecognitionResult result) {
        final words = result.recognizedWords.trim();
        if (words.isNotEmpty) {
          // 중간 결과 콜백
          if (!result.finalResult && onPartialResult != null) {
            onPartialResult(words);
          }
          if (result.finalResult) {
            recognized = words;
            lastConfidence = result.confidence;
          }
        }
      },
      localeId: AppConstants.sttLocale,
      listenFor: Duration(seconds: timeoutSeconds),
      pauseFor: const Duration(seconds: 2),
    );

    // 타임아웃 또는 자동 완료 대기
    await Future.delayed(Duration(seconds: timeoutSeconds));

    if (_stt.isListening) {
      await _stt.stop();
    }

    _isListening = false;
    notifyListeners();

    // 신뢰도 필터링
    if (recognized.isEmpty) return null;
    if (lastConfidence > 0 && lastConfidence < _confidenceThreshold) {
      debugPrint('STT 신뢰도 낮음 ($lastConfidence) — 무시: "$recognized"');
      return null;
    }
    return recognized;
  }

  /// 음성 인식을 즉시 중단합니다.
  Future<void> stopListening() async {
    if (_stt.isListening) {
      await _stt.stop();
      _isListening = false;
      notifyListeners();
    }
  }

  @override
  Future<void> dispose() async {
    await _tts.stop();
    if (_stt.isListening) await _stt.stop();
    super.dispose();
  }
}
