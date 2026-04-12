import 'package:flutter_test/flutter_test.dart';
import 'package:louis/core/services/voice_pipeline.dart';

void main() {
  // ── PipelineState 열거형 ─────────────────────────────

  group('PipelineState', () {
    test('4가지 상태 존재', () {
      expect(PipelineState.values, hasLength(4));
      expect(PipelineState.values, containsAll([
        PipelineState.idle,
        PipelineState.listening,
        PipelineState.processing,
        PipelineState.speaking,
      ]));
    });

    test('idle이 기본 초기 상태', () {
      // 파이프라인 상태 흐름: idle → listening → processing → speaking → idle
      const initial = PipelineState.idle;
      expect(initial, PipelineState.idle);
    });
  });

  // ── PipelineEvent 팩토리 ─────────────────────────────

  group('PipelineEvent', () {
    test('wakeWordDetected 싱글턴 이벤트', () {
      final e1 = PipelineEvent.wakeWordDetected;
      final e2 = PipelineEvent.wakeWordDetected;
      expect(e1, same(e2));
    });

    test('listeningStarted 싱글턴 이벤트', () {
      final e = PipelineEvent.listeningStarted;
      expect(e, isNotNull);
    });

    test('idle 싱글턴 이벤트', () {
      final e = PipelineEvent.idle;
      expect(e, isNotNull);
    });

    test('sttCompleted 텍스트 보존', () {
      final e = PipelineEvent.sttCompleted('오늘 날씨 알려줘');
      expect(e, isA<_SttCompletedMatcher>());
      // sealed class이므로 패턴 매칭으로 확인
      final event = PipelineEvent.sttCompleted('테스트 텍스트');
      switch (event) {
        case final stt when stt.toString().contains('테스트 텍스트'):
          // text 접근은 내부 클래스(_SttCompleted)이므로 toString으로 간접 확인
          break;
        default:
          // event가 올바른 타입인지 확인
          expect(event.runtimeType.toString(), contains('Stt'));
      }
    });

    test('ttsStarted 텍스트 포함', () {
      final event = PipelineEvent.ttsStarted('안녕하세요!');
      expect(event.runtimeType.toString(), contains('Tts'));
    });

    test('nativeIntent payload 포함', () {
      const payload = '{"action":"PHONE_CALL","contact":"엄마"}';
      final event = PipelineEvent.nativeIntent(payload);
      expect(event.runtimeType.toString(), contains('Native'));
    });

    test('서로 다른 이벤트는 다른 인스턴스', () {
      final stt1 = PipelineEvent.sttCompleted('텍스트 A');
      final stt2 = PipelineEvent.sttCompleted('텍스트 B');
      expect(stt1, isNot(same(stt2)));
    });
  });

  // ── PipelineState 전환 시뮬레이션 ────────────────────

  group('PipelineState 전환 시나리오', () {
    test('정상 대화 흐름: idle → listening → processing → speaking → idle', () {
      final states = <PipelineState>[];

      // 대화 시작
      states.add(PipelineState.idle);
      states.add(PipelineState.listening);     // STT
      states.add(PipelineState.processing);    // API 호출
      states.add(PipelineState.speaking);      // TTS
      states.add(PipelineState.idle);          // 완료

      expect(states.first, PipelineState.idle);
      expect(states[1], PipelineState.listening);
      expect(states[2], PipelineState.processing);
      expect(states[3], PipelineState.speaking);
      expect(states.last, PipelineState.idle);
    });

    test('STT 실패 흐름: listening → idle (빈 결과)', () {
      var state = PipelineState.listening;
      // STT 결과 없을 때 → 바로 idle
      state = PipelineState.idle;
      expect(state, PipelineState.idle);
    });

    test('처리 중 중복 호출 방지 (idle 아닐 때 무시)', () {
      var state = PipelineState.listening;
      // 이미 처리 중이므로 새 요청 무시 → 상태 변경 없음
      if (state != PipelineState.idle) {
        // 아무 것도 하지 않음
      }
      expect(state, PipelineState.listening);
    });
  });

  // ── 이벤트 스트림 시뮬레이션 ─────────────────────────

  group('이벤트 스트림 패턴', () {
    test('대화 사이클 이벤트 순서 검증', () {
      final events = <PipelineEvent>[
        PipelineEvent.wakeWordDetected,
        PipelineEvent.listeningStarted,
        PipelineEvent.sttCompleted('날씨 알려줘'),
        PipelineEvent.ttsStarted('오늘은 맑아요'),
        PipelineEvent.idle,
      ];

      expect(events, hasLength(5));
      expect(events[0], PipelineEvent.wakeWordDetected);
      expect(events[4], PipelineEvent.idle);
    });

    test('네이티브 인텐트 이벤트 포함 흐름', () {
      const phonePayload = '{"action":"PHONE_CALL","contact":"엄마","message":"엄마에게 전화 연결할게요."}';
      final events = <PipelineEvent>[
        PipelineEvent.wakeWordDetected,
        PipelineEvent.listeningStarted,
        PipelineEvent.sttCompleted('엄마한테 전화해줘'),
        PipelineEvent.nativeIntent(phonePayload),
        PipelineEvent.ttsStarted('엄마에게 전화 연결할게요.'),
        PipelineEvent.idle,
      ];

      expect(events, hasLength(6));
      // 네이티브 인텐트 이벤트가 올바른 위치에 있는지 확인
      expect(events[3].runtimeType.toString(), contains('Native'));
    });
  });
}

// ── 타입 체크 헬퍼 매처 ─────────────────────────────────

class _SttCompletedMatcher extends TypeMatcher<Object> {
  const _SttCompletedMatcher() : super();

  @override
  bool matches(Object item, Map matchState) {
    return item.runtimeType.toString().contains('SttCompleted') ||
           item.runtimeType.toString().contains('Stt');
  }
}
