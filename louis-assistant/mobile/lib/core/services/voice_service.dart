import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import '../constants.dart';

/// 음성 입출력 서비스
/// STT (음성 → 텍스트) + TTS (텍스트 → 음성)
class VoiceService extends ChangeNotifier {
  final _tts = FlutterTts();
  final _stt = SpeechToText();

  bool _isSpeaking = false;
  bool _isListening = false;
  bool _sttAvailable = false;

  bool get isSpeaking => _isSpeaking;
  bool get isListening => _isListening;

  Future<void> initialize() async {
    // TTS 초기화
    await _tts.setLanguage('ko-KR');
    await _tts.setSpeechRate(AppConstants.ttsRate);
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

    // STT 초기화
    _sttAvailable = await _stt.initialize(
      onError: (err) => debugPrint('STT 오류: $err'),
    );
  }

  /// 텍스트를 음성으로 읽어줍니다.
  Future<void> speak(String text) async {
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
  Future<String?> listen({int timeoutSeconds = AppConstants.sttTimeoutSeconds}) async {
    if (!_sttAvailable) return null;

    String recognized = '';
    _isListening = true;
    notifyListeners();

    await _stt.listen(
      onResult: (result) {
        recognized = result.recognizedWords;
      },
      localeId: AppConstants.sttLocale,
      listenFor: Duration(seconds: timeoutSeconds),
      pauseFor: const Duration(seconds: 2),
    );

    // 음성 인식 완료 대기
    await Future.delayed(Duration(seconds: timeoutSeconds));
    await _stt.stop();
    _isListening = false;
    notifyListeners();

    return recognized.trim().isEmpty ? null : recognized.trim();
  }

  Future<void> dispose() async {
    await _tts.stop();
    await _stt.stop();
    super.dispose();
  }
}
