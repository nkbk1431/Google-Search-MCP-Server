import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:louis/core/widgets/waveform_widget.dart';

void main() {
  // ── WaveformWidget 테스트 ────────────────────────────────

  group('WaveformWidget', () {
    testWidgets('기본 파라미터로 렌더링됨', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: WaveformWidget(color: Colors.blue),
            ),
          ),
        ),
      );
      expect(find.byType(WaveformWidget), findsOneWidget);
    });

    testWidgets('barCount 개수만큼 Container가 생성됨', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: Colors.red, barCount: 7),
          ),
        ),
      );
      // Row 안에 7개의 Container(막대)가 있어야 합니다
      final row = tester.widget<Row>(
        find.descendant(of: find.byType(WaveformWidget), matching: find.byType(Row)),
      );
      expect(row.children.length, 7);
    });

    testWidgets('기본 barCount는 5', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: Colors.green),
          ),
        ),
      );
      final row = tester.widget<Row>(
        find.descendant(of: find.byType(WaveformWidget), matching: find.byType(Row)),
      );
      expect(row.children.length, 5);
    });

    testWidgets('AnimatedBuilder가 포함됨', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: Colors.purple),
          ),
        ),
      );
      expect(find.byType(AnimatedBuilder), findsAtLeastNWidgets(1));
    });

    testWidgets('주어진 색상이 Container에 적용됨', (tester) async {
      const testColor = Colors.orange;
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: testColor, barCount: 1),
          ),
        ),
      );
      // 하나의 막대 Container를 찾아 색상이 testColor인지 확인
      final containers = tester.widgetList<Container>(
        find.descendant(
          of: find.byType(Row),
          matching: find.byType(Container),
        ),
      ).toList();
      expect(containers, isNotEmpty);
      final box = containers.first.decoration as BoxDecoration;
      expect(box.color, testColor);
    });

    testWidgets('애니메이션 1프레임 후 막대 높이가 유효함', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: Colors.teal, height: 40),
          ),
        ),
      );
      // 애니메이션 1프레임 진행
      await tester.pump(const Duration(milliseconds: 100));

      final containers = tester.widgetList<Container>(
        find.descendant(of: find.byType(Row), matching: find.byType(Container)),
      ).toList();
      for (final c in containers) {
        expect(c.constraints?.maxHeight ?? double.infinity, greaterThan(0));
      }
    });

    testWidgets('커스텀 barWidth와 spacing 적용', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(
              color: Colors.blue,
              barCount: 3,
              barWidth: 8,
              spacing: 6,
            ),
          ),
        ),
      );
      expect(find.byType(WaveformWidget), findsOneWidget);
      // 3개의 막대가 있어야 합니다
      final row = tester.widget<Row>(
        find.descendant(of: find.byType(WaveformWidget), matching: find.byType(Row)),
      );
      expect(row.children.length, 3);
    });

    testWidgets('dispose 시 메모리 누수 없음', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WaveformWidget(color: Colors.blue),
          ),
        ),
      );
      // 위젯 제거 — dispose()가 정상 실행되어야 합니다
      await tester.pumpWidget(const SizedBox());
    });
  });

  // ── PulseRingWidget 테스트 ───────────────────────────────

  group('PulseRingWidget', () {
    testWidgets('기본 렌더링', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.blue,
              size: 60,
              child: const Icon(Icons.mic),
            ),
          ),
        ),
      );
      expect(find.byType(PulseRingWidget), findsOneWidget);
    });

    testWidgets('child 위젯이 렌더링됨', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.red,
              size: 50,
              child: const Icon(Icons.mic, key: Key('mic-icon')),
            ),
          ),
        ),
      );
      expect(find.byKey(const Key('mic-icon')), findsOneWidget);
    });

    testWidgets('SizedBox 크기는 size * 1.6', (tester) async {
      const size = 60.0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.blue,
              size: size,
              child: const SizedBox.shrink(),
            ),
          ),
        ),
      );
      final sizedBox = tester.widget<SizedBox>(
        find.descendant(
          of: find.byType(PulseRingWidget),
          matching: find.byType(SizedBox).first,
        ),
      );
      expect(sizedBox.width, size * 1.6);
      expect(sizedBox.height, size * 1.6);
    });

    testWidgets('Stack과 AnimatedBuilder 포함', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.green,
              size: 56,
              child: const Icon(Icons.mic),
            ),
          ),
        ),
      );
      expect(find.byType(Stack), findsAtLeastNWidgets(1));
      expect(find.byType(AnimatedBuilder), findsAtLeastNWidgets(1));
    });

    testWidgets('애니메이션 여러 프레임 후 정상 동작', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.purple,
              size: 64,
              child: const Icon(Icons.mic),
            ),
          ),
        ),
      );
      // 여러 프레임 진행
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.byType(PulseRingWidget), findsOneWidget);
    });

    testWidgets('dispose 시 메모리 누수 없음', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PulseRingWidget(
              color: Colors.blue,
              size: 50,
              child: const Icon(Icons.mic),
            ),
          ),
        ),
      );
      await tester.pumpWidget(const SizedBox());
    });
  });
}
