import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:louis/features/tasks/tasks_provider.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  // ── TodoNotifier ───────────────────────────────────────────────────

  group('TodoNotifier', () {
    ProviderContainer makeContainer() => ProviderContainer();

    test('초기 상태는 빈 목록', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);
      expect(c.read(todoProvider), isEmpty);
    });

    test('할일 추가', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).add('테스트 할일');
      final todos = c.read(todoProvider);
      expect(todos, hasLength(1));
      expect(todos.first.content, '테스트 할일');
      expect(todos.first.done, false);
    });

    test('할일 완료 토글', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).add('토글 테스트');
      final id = c.read(todoProvider).first.id;

      c.read(todoProvider.notifier).toggle(id);
      expect(c.read(todoProvider).first.done, true);

      c.read(todoProvider.notifier).toggle(id);
      expect(c.read(todoProvider).first.done, false);
    });

    test('할일 삭제', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).add('삭제할 할일');
      final id = c.read(todoProvider).first.id;

      c.read(todoProvider.notifier).remove(id);
      expect(c.read(todoProvider), isEmpty);
    });

    test('최신 항목이 목록 앞에 위치', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).add('A');
      c.read(todoProvider.notifier).add('B');
      expect(c.read(todoProvider).first.content, 'B');
    });

    test('존재하지 않는 ID 토글은 무시됨', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).add('항목');
      expect(() => c.read(todoProvider.notifier).toggle(9999), returnsNormally);
    });

    test('syncFromAgent는 add와 동일', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      c.read(todoProvider.notifier).syncFromAgent('에이전트 할일');
      expect(c.read(todoProvider).first.content, '에이전트 할일');
    });
  });

  // ── ReminderNotifier ───────────────────────────────────────────────

  group('ReminderNotifier', () {
    ProviderContainer makeContainer() => ProviderContainer();

    test('초기 상태는 빈 목록', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);
      expect(c.read(reminderProvider), isEmpty);
    });

    test('리마인더 추가', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      final trigger = DateTime.now().add(const Duration(minutes: 30));
      c.read(reminderProvider.notifier).add('약 먹기', trigger);

      final reminders = c.read(reminderProvider);
      expect(reminders, hasLength(1));
      expect(reminders.first.content, '약 먹기');
      expect(reminders.first.fired, false);
    });

    test('리마인더 발화 표시', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      final trigger = DateTime.now().add(const Duration(minutes: 5));
      c.read(reminderProvider.notifier).add('회의', trigger);
      final id = c.read(reminderProvider).first.id;

      c.read(reminderProvider.notifier).markFired(id);
      expect(c.read(reminderProvider).first.fired, true);
    });

    test('리마인더 삭제', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      final trigger = DateTime.now().add(const Duration(hours: 1));
      c.read(reminderProvider.notifier).add('삭제 테스트', trigger);
      final id = c.read(reminderProvider).first.id;

      c.read(reminderProvider.notifier).remove(id);
      expect(c.read(reminderProvider), isEmpty);
    });
  });

  // ── 모델 직렬화 ─────────────────────────────────────────────────────

  group('TodoItem 직렬화', () {
    test('toJson / fromJson 왕복', () {
      final item = TodoItem(
        id: 42,
        content: '직렬화 테스트',
        done: true,
        createdAt: DateTime(2025, 3, 15, 10, 30),
      );
      final json = item.toJson();
      final restored = TodoItem.fromJson(json);

      expect(restored.id, item.id);
      expect(restored.content, item.content);
      expect(restored.done, item.done);
      expect(restored.createdAt, item.createdAt);
    });
  });

  group('ReminderItem 직렬화', () {
    test('toJson / fromJson 왕복', () {
      final item = ReminderItem(
        id: 7,
        content: '리마인더 직렬화',
        triggerAt: DateTime(2025, 6, 1, 14, 0),
        fired: false,
      );
      final json = item.toJson();
      final restored = ReminderItem.fromJson(json);

      expect(restored.id, item.id);
      expect(restored.content, item.content);
      expect(restored.triggerAt, item.triggerAt);
      expect(restored.fired, item.fired);
    });
  });
}
