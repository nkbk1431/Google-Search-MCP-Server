import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:louis/features/chat/chat_provider.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  // ── ChatMessage 단위 테스트 ───────────────────────────

  group('ChatMessage', () {
    test('기본 타임스탬프는 현재 시각', () {
      final msg = ChatMessage(text: '안녕', role: MessageRole.user);
      final now = DateTime.now();
      expect(msg.timestamp.difference(now).inSeconds.abs(), lessThanOrEqualTo(1));
    });

    test('명시적 타임스탬프 보존', () {
      final ts = DateTime(2026, 4, 12, 10, 0, 0);
      final msg = ChatMessage(text: '안녕', role: MessageRole.user, timestamp: ts);
      expect(msg.timestamp, ts);
    });

    test('isOfflineNotice 기본값 false', () {
      final msg = ChatMessage(text: '테스트', role: MessageRole.assistant);
      expect(msg.isOfflineNotice, isFalse);
    });

    test('오프라인 알림 메시지 생성', () {
      final msg = ChatMessage(
        text: '오프라인입니다',
        role: MessageRole.assistant,
        isOfflineNotice: true,
      );
      expect(msg.isOfflineNotice, isTrue);
    });

    test('toolCalls 기본값 빈 리스트', () {
      final msg = ChatMessage(text: 'test', role: MessageRole.user);
      expect(msg.toolCalls, isEmpty);
    });
  });

  // ── ChatState 단위 테스트 ────────────────────────────

  group('ChatState', () {
    test('초기 상태 기본값', () {
      const state = ChatState();
      expect(state.messages, isEmpty);
      expect(state.voiceState, VoiceState.idle);
      expect(state.isOffline, isFalse);
      expect(state.errorMessage, isNull);
    });

    test('copyWith - 메시지 목록 변경', () {
      const state = ChatState();
      final msg = ChatMessage(text: '안녕', role: MessageRole.user);
      final next = state.copyWith(messages: [msg]);
      expect(next.messages, hasLength(1));
      expect(next.voiceState, VoiceState.idle); // 유지
    });

    test('copyWith - voiceState 변경', () {
      const state = ChatState();
      final next = state.copyWith(voiceState: VoiceState.listening);
      expect(next.voiceState, VoiceState.listening);
      expect(next.messages, isEmpty); // 유지
    });

    test('copyWith - isOffline 변경', () {
      const state = ChatState();
      final next = state.copyWith(isOffline: true);
      expect(next.isOffline, isTrue);
    });

    test('copyWith - errorMessage null 명시 초기화', () {
      const state = ChatState(errorMessage: '이전 오류');
      final next = state.copyWith(errorMessage: null);
      expect(next.errorMessage, isNull);
    });

    test('여러 메시지 누적', () {
      const state = ChatState();
      final msgs = [
        ChatMessage(text: '안녕', role: MessageRole.user),
        ChatMessage(text: '안녕하세요!', role: MessageRole.assistant),
        ChatMessage(text: '날씨 알려줘', role: MessageRole.user),
      ];
      final next = state.copyWith(messages: msgs);
      expect(next.messages, hasLength(3));
      expect(next.messages[0].role, MessageRole.user);
      expect(next.messages[1].role, MessageRole.assistant);
    });
  });

  // ── VoiceState 열거형 ────────────────────────────────

  group('VoiceState', () {
    test('4가지 상태 존재', () {
      expect(VoiceState.values, hasLength(4));
      expect(VoiceState.values, containsAll([
        VoiceState.idle,
        VoiceState.listening,
        VoiceState.processing,
        VoiceState.speaking,
      ]));
    });
  });

  // ── MessageRole 열거형 ───────────────────────────────

  group('MessageRole', () {
    test('user 와 assistant 두 역할', () {
      expect(MessageRole.values, hasLength(2));
      expect(MessageRole.values, contains(MessageRole.user));
      expect(MessageRole.values, contains(MessageRole.assistant));
    });
  });

  // ── ChatNotifier.clearHistory ───────────────���─────────
  // 주의: ChatNotifier는 ApiClient, VoiceService에 의존하므로
  // 단위 테스트는 상태 모델 중심으로, 통합 테스트는 별도 진행합니다.

  group('ChatState 시나리오', () {
    test('메시지 추가 후 clearHistory 패턴', () {
      // ChatNotifier 대신 ChatState 직접 조작으로 검증
      var state = const ChatState();

      // 메시지 추가
      final userMsg = ChatMessage(text: '오늘 날씨?', role: MessageRole.user);
      state = state.copyWith(messages: [...state.messages, userMsg]);
      expect(state.messages, hasLength(1));

      final aiMsg = ChatMessage(text: '맑아요!', role: MessageRole.assistant);
      state = state.copyWith(messages: [...state.messages, aiMsg]);
      expect(state.messages, hasLength(2));

      // clearHistory
      state = const ChatState();
      expect(state.messages, isEmpty);
      expect(state.voiceState, VoiceState.idle);
    });

    test('오프라인 상태에서 오프라인 알림 버블 추가 패턴', () {
      var state = const ChatState();

      const offlineMsg = '인터넷 연결이 없어요.';
      final offlineBubble = ChatMessage(
        text: offlineMsg,
        role: MessageRole.assistant,
        isOfflineNotice: true,
      );
      state = state.copyWith(
        messages: [offlineBubble],
        isOffline: true,
        voiceState: VoiceState.idle,
      );

      expect(state.isOffline, isTrue);
      expect(state.messages.first.isOfflineNotice, isTrue);
      expect(state.messages.first.text, offlineMsg);
    });

    test('음성 처리 흐름 상태 전환 시뮬레이션', () {
      var state = const ChatState();

      // idle → listening
      state = state.copyWith(voiceState: VoiceState.listening);
      expect(state.voiceState, VoiceState.listening);

      // listening → processing
      state = state.copyWith(voiceState: VoiceState.processing);
      expect(state.voiceState, VoiceState.processing);

      // processing → speaking (응답 추가)
      final reply = ChatMessage(text: '안녕하세요!', role: MessageRole.assistant);
      state = state.copyWith(
        messages: [reply],
        voiceState: VoiceState.speaking,
      );
      expect(state.voiceState, VoiceState.speaking);
      expect(state.messages, hasLength(1));

      // speaking → idle
      state = state.copyWith(voiceState: VoiceState.idle);
      expect(state.voiceState, VoiceState.idle);
    });
  });
}
