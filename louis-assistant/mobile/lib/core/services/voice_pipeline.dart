import 'dart:async';
import 'package:flutter/foundation.dart';
import 'api_client.dart';
import 'voice_service.dart';
import 'wake_word_service.dart';
import 'foreground_service.dart';

/// 음성 파이프라인 오케스트레이터
/// 웨이크워드 → STT → API → TTS 전체 흐름을 관리합니다.
class VoicePipeline extends ChangeNotifier {
  final VoiceService _voice;
  final WakeWordService _wakeWord;
  final ApiClient _api = ApiClient();
  final LouisForegroundService _fg = LouisForegroundService.instance;

  PipelineState _state = PipelineState.idle;
  String? _lastError;
  String _sessionId = 'default';

  /// 파이프라인 이벤트 스트림 (UI 애니메이션, 디버깅 용도)
  final _eventController = StreamController<PipelineEvent>.broadcast();
  Stream<PipelineEvent> get events => _eventController.stream;

  PipelineState get state => _state;
  String? get lastError => _lastError;

  VoicePipeline({
    required VoiceService voice,
    required WakeWordService wakeWord,
    required String sessionId,
  })  : _voice = voice,
        _wakeWord = wakeWord,
        _sessionId = sessionId;

  /// 파이프라인을 초기화하고 웨이크워드 감지를 시작합니다.
  Future<void> initialize() async {
    await _voice.initialize();
    await _fg.initialize();

    // 포그라운드 서비스 시작 (백그라운드 웨이크워드 유지)
    await _fg.start();

    // 웨이크워드 감지 시작 (버튼 트리거 모드)
    await _wakeWord.start(
      onWakeWord: _onWakeWordDetected,
    );

    _setState(PipelineState.idle);
    debugPrint('[VoicePipeline] 초기화 완료');
  }

  /// 웨이크워드 감지 콜백
  void _onWakeWordDetected() {
    if (_state != PipelineState.idle) return; // 이미 처리 중이면 무시
    _emit(PipelineEvent.wakeWordDetected);
    startConversation();
  }

  /// 대화 사이클: STT → API → TTS
  Future<void> startConversation() async {
    if (_state != PipelineState.idle) return;

    // 1. TTS 중단
    if (_voice.isSpeaking) await _voice.stop();

    // 2. 웨이크워드 일시 중지 (마이크 충돌 방지)
    await _wakeWord.pause();
    await _fg.updateNotification('듣는 중...');

    // 3. STT
    _setState(PipelineState.listening);
    _emit(PipelineEvent.listeningStarted);
    final userText = await _voice.listen();

    if (userText == null || userText.trim().isEmpty) {
      await _voice.speak('잘 못 들었어요. 다시 불러주세요.');
      await _reset();
      return;
    }

    debugPrint('[Pipeline] 인식: $userText');
    _emit(PipelineEvent.sttCompleted(userText));

    // 4. API 호출
    _setState(PipelineState.processing);
    await _fg.updateNotification('처리 중...');

    try {
      final response = await _api.chat(userText, sessionId: _sessionId);
      final reply = response.reply;

      // 5. 인텐트 처리 (전화/문자 등 네이티브 동작)
      _handleNativeIntent(response.toolCalls);

      // 6. TTS
      _setState(PipelineState.speaking);
      await _fg.updateNotification('말하는 중...');
      _emit(PipelineEvent.ttsStarted(reply));
      await _voice.speak(reply);

    } catch (e) {
      _lastError = e.toString();
      const errMsg = '서버에 연결할 수 없어요. 인터넷 연결을 확인해주세요.';
      await _voice.speak(errMsg);
    } finally {
      await _reset();
    }
  }

  void _handleNativeIntent(List<Map<String, dynamic>> toolCalls) {
    // 전화/문자 인텐트 처리는 platform channel로 위임
    for (final call in toolCalls) {
      final result = call['result'] as String? ?? '';
      if (result.contains('"action": "PHONE_CALL"') ||
          result.contains('"action": "SEND_SMS"')) {
        _emit(PipelineEvent.nativeIntent(result));
      }
    }
  }

  Future<void> _reset() async {
    await _wakeWord.resume();
    await _fg.updateNotification('"루이스"라고 불러주세요');
    _setState(PipelineState.idle);
    _emit(PipelineEvent.idle);
  }

  void _setState(PipelineState s) {
    _state = s;
    notifyListeners();
  }

  void _emit(PipelineEvent event) {
    if (!_eventController.isClosed) {
      _eventController.add(event);
    }
  }

  @override
  Future<void> dispose() async {
    await _wakeWord.dispose();
    await _voice.dispose();
    await _fg.stop();
    await _eventController.close();
    super.dispose();
  }
}

// ── 파이프라인 상태 ─────────────────────────────────────────────────

enum PipelineState { idle, listening, processing, speaking }

// ── 파이프라인 이벤트 ───────────────────────────────────────────────

sealed class PipelineEvent {
  const PipelineEvent();

  static const wakeWordDetected = _WakeWordDetected();
  static const listeningStarted = _ListeningStarted();
  static const idle = _Idle();
  static _SttCompleted sttCompleted(String text) => _SttCompleted(text);
  static _TtsStarted ttsStarted(String text) => _TtsStarted(text);
  static _NativeIntent nativeIntent(String payload) => _NativeIntent(payload);
}

class _WakeWordDetected extends PipelineEvent { const _WakeWordDetected(); }
class _ListeningStarted extends PipelineEvent { const _ListeningStarted(); }
class _Idle extends PipelineEvent { const _Idle(); }
class _SttCompleted extends PipelineEvent {
  final String text;
  const _SttCompleted(this.text);
}
class _TtsStarted extends PipelineEvent {
  final String text;
  const _TtsStarted(this.text);
}
class _NativeIntent extends PipelineEvent {
  final String payload;
  const _NativeIntent(this.payload);
}
