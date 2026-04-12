import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:louis/features/memo/memo_provider.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  ProviderContainer makeContainer() => ProviderContainer();

  group('MemoNotifier', () {
    test('초기 상태는 빈 목록', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero); // _load() 완료 대기
      expect(container.read(memoProvider), isEmpty);
    });

    test('메모 추가 후 목록에 포함됨', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('테스트 메모');
      final memos = container.read(memoProvider);

      expect(memos, hasLength(1));
      expect(memos.first.content, '테스트 메모');
      expect(memos.first.done, isFalse); // MemoItem has no done field, just checking
    });

    test('빈 내용 추가는 무시됨', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('   ');
      expect(container.read(memoProvider), isEmpty);
    });

    test('메모 삭제', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('삭제할 메모');
      final id = container.read(memoProvider).first.id;

      container.read(memoProvider.notifier).remove(id);
      expect(container.read(memoProvider), isEmpty);
    });

    test('메모 수정', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('원본 내용');
      final id = container.read(memoProvider).first.id;

      container.read(memoProvider.notifier).update(id, '수정된 내용');
      expect(container.read(memoProvider).first.content, '수정된 내용');
    });

    test('여러 메모 추가 시 최신 메모가 앞에 위치', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('첫 번째');
      container.read(memoProvider.notifier).add('두 번째');

      final memos = container.read(memoProvider);
      expect(memos.first.content, '두 번째');
      expect(memos.last.content, '첫 번째');
    });

    test('검색 기능 — 일치하는 메모만 반환', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('오늘 장보기');
      container.read(memoProvider.notifier).add('회의 준비');
      container.read(memoProvider.notifier).add('장보기 목록 확인');

      final results = container.read(memoProvider.notifier).search('장보기');
      expect(results, hasLength(2));
    });

    test('검색 빈 쿼리 시 전체 반환', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('메모 1');
      container.read(memoProvider.notifier).add('메모 2');

      final results = container.read(memoProvider.notifier).search('');
      expect(results, hasLength(2));
    });

    test('syncFromAgent는 add와 동일하게 동작', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).syncFromAgent('에이전트 메모');
      expect(container.read(memoProvider).first.content, '에이전트 메모');
    });

    test('고유 ID 자동 증가', () async {
      final container = makeContainer();
      addTearDown(container.dispose);
      await Future.delayed(Duration.zero);

      container.read(memoProvider.notifier).add('메모 A');
      container.read(memoProvider.notifier).add('메모 B');

      final ids = container.read(memoProvider).map((m) => m.id).toSet();
      expect(ids, hasLength(2));
    });
  });
}
