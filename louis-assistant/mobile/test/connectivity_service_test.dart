import 'package:flutter_test/flutter_test.dart';
import 'package:louis/core/services/connectivity_service.dart';

void main() {
  group('ConnectivityService 메시지 큐', () {
    late ConnectivityService svc;

    setUp(() {
      // 싱글턴 리셋을 위해 리플렉션 없이 직접 인스턴스 생성
      // (테스트에서는 실제 Connectivity 플러그인이 없으므로 큐 로직만 검증)
    });

    test('오프라인 상태에서 메시지 큐에 추가됨', () {
      final svc = ConnectivityService();
      svc.enqueue('안녕하세요', 'session-1');
      svc.enqueue('날씨 어때?', 'session-1');

      expect(svc.queuedMessages, hasLength(2));
      expect(svc.queuedMessages[0].text, '안녕하세요');
      expect(svc.queuedMessages[1].text, '날씨 어때?');
    });

    test('drainQueue 후 큐가 비워짐', () {
      final svc = ConnectivityService();
      svc.enqueue('메시지 1', 'session-1');
      svc.enqueue('메시지 2', 'session-1');

      final drained = svc.drainQueue();
      expect(drained, hasLength(2));
      expect(svc.queuedMessages, isEmpty);
    });

    test('drainQueue 반환값에 올바른 텍스트 포함', () {
      final svc = ConnectivityService();
      svc.enqueue('테스트 메시지', 'session-abc');

      final drained = svc.drainQueue();
      expect(drained.first.text, '테스트 메시지');
      expect(drained.first.sessionId, 'session-abc');
    });

    test('빈 큐에서 drainQueue는 빈 목록 반환', () {
      final svc = ConnectivityService();
      final drained = svc.drainQueue();
      expect(drained, isEmpty);
    });

    test('큐 메시지에 타임스탬프 포함', () {
      final before = DateTime.now();
      final svc = ConnectivityService();
      svc.enqueue('타임스탬프 테스트', 's1');
      final after = DateTime.now();

      final msg = svc.queuedMessages.first;
      expect(
        msg.queuedAt.isAfter(before.subtract(const Duration(seconds: 1))),
        isTrue,
      );
      expect(
        msg.queuedAt.isBefore(after.add(const Duration(seconds: 1))),
        isTrue,
      );
    });
  });
}
