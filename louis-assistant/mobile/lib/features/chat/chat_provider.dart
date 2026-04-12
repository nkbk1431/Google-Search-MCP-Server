import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/services/api_client.dart';
import '../../core/services/voice_service.dart';

// ── 메시지 모델 ──────────────────────────────────────────��─────────

enum MessageRole { user, assistant }

enum VoiceState { idle, listening, processing, speaking }

class ChatMessage {
  final String text;
  final MessageRole role;
  final DateTime timestamp;
  final List<Map<String, dynamic>> toolCalls;

  ChatMessage({
    required this.text,
    required this.role,
    DateTime? timestamp,
    this.toolCalls = const [],
  }) : timestamp = timestamp ?? DateTime.now();
}

// ── 상태 클래스 ────────────────────────────────────────────────────

class ChatState {
  final List<ChatMessage> messages;
  final VoiceState voiceState;
  final String? errorMessage;

  const ChatState({
    this.messages = const [],
    this.voiceState = VoiceState.idle,
    this.errorMessage,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    VoiceState? voiceState,
    String? errorMessage,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      voiceState: voiceState ?? this.voiceState,
      errorMessage: errorMessage,
    );
  }
}

// ── Notifier ────────────────────────────────────────────────────────

class ChatNotifier extends StateNotifier<ChatState> {
  final ApiClient _api = ApiClient();
  final VoiceService _voice;
  final String _sessionId;

  ChatNotifier({required VoiceService voice, required String sessionId})
      : _voice = voice,
        _sessionId = sessionId,
        super(const ChatState());

  /// 웨이크워드 감지 후 음성 입력 → API → TTS 전체 파이프라인
  Future<void> handleWakeWord() async {
    // 1. 상태: 듣는 중
    state = state.copyWith(voiceState: VoiceState.listening);

    // TTS 중단
    if (_voice.isSpeaking) await _voice.stop();

    // 2. STT
    final userText = await _voice.listen();
    if (userText == null || userText.isEmpty) {
      await _voice.speak('잘 못 들었어요. 다시 불러주세요.');
      state = state.copyWith(voiceState: VoiceState.idle);
      return;
    }

    await _sendMessage(userText);
  }

  /// 텍스트로 메시지 전송 (UI 텍스트 입력용)
  Future<void> sendText(String text) async {
    if (text.trim().isEmpty) return;
    await _sendMessage(text.trim());
  }

  Future<void> _sendMessage(String userText) async {
    // 사용자 메시지 추가
    state = state.copyWith(
      messages: [...state.messages, ChatMessage(text: userText, role: MessageRole.user)],
      voiceState: VoiceState.processing,
    );

    try {
      // 3. API 호출
      final response = await _api.chat(userText, sessionId: _sessionId);
      final reply = response.reply;

      // 루이스 응답 추가
      state = state.copyWith(
        messages: [
          ...state.messages,
          ChatMessage(
            text: reply,
            role: MessageRole.assistant,
            toolCalls: response.toolCalls,
          ),
        ],
        voiceState: VoiceState.speaking,
      );

      // 4. TTS
      await _voice.speak(reply);
      state = state.copyWith(voiceState: VoiceState.idle);

    } on Exception catch (e) {
      const errMsg = '일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요.';
      state = state.copyWith(
        messages: [
          ...state.messages,
          ChatMessage(text: errMsg, role: MessageRole.assistant),
        ],
        voiceState: VoiceState.idle,
        errorMessage: e.toString(),
      );
      await _voice.speak(errMsg);
    }
  }

  void clearHistory() {
    state = const ChatState();
  }
}

// ── Providers ──────────────────────────────────────────────────────

final voiceServiceProvider = ChangeNotifierProvider<VoiceService>((ref) {
  final service = VoiceService();
  service.initialize();
  return service;
});

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  final voice = ref.watch(voiceServiceProvider);
  return ChatNotifier(voice: voice, sessionId: 'app-session-1');
});
