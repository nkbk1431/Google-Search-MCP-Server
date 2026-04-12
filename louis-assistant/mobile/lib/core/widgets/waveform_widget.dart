import 'dart:math' as math;
import 'package:flutter/material.dart';

/// 음성 인식/출력 시 표시되는 파형 애니메이션 위젯
///
/// [barCount] 개의 막대가 서로 다른 위상(phase)으로 진동합니다.
class WaveformWidget extends StatefulWidget {
  final Color color;
  final int barCount;
  final double height;
  final double barWidth;
  final double spacing;

  const WaveformWidget({
    super.key,
    required this.color,
    this.barCount = 5,
    this.height = 28,
    this.barWidth = 4,
    this.spacing = 3,
  });

  @override
  State<WaveformWidget> createState() => _WaveformWidgetState();
}

class _WaveformWidgetState extends State<WaveformWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: List.generate(widget.barCount, (i) {
            // 각 막대마다 위상 차이를 두어 물결 효과 생성
            final phase = (i / widget.barCount) * 2 * math.pi;
            final t = _controller.value * 2 * math.pi;
            // 진폭: 0.2 ~ 1.0 사이에서 진동
            final amplitude = 0.2 + 0.8 * ((math.sin(t + phase) + 1) / 2);
            final barHeight = widget.height * amplitude;

            return Container(
              width: widget.barWidth,
              height: barHeight,
              margin: EdgeInsets.symmetric(horizontal: widget.spacing / 2),
              decoration: BoxDecoration(
                color: widget.color,
                borderRadius: BorderRadius.circular(widget.barWidth / 2),
              ),
            );
          }),
        );
      },
    );
  }
}

/// 채팅 화면 하단 마이크 버튼 주변에 표시되는 원형 파동 애니메이션
class PulseRingWidget extends StatefulWidget {
  final Color color;
  final double size;
  final Widget child;

  const PulseRingWidget({
    super.key,
    required this.color,
    required this.size,
    required this.child,
  });

  @override
  State<PulseRingWidget> createState() => _PulseRingWidgetState();
}

class _PulseRingWidgetState extends State<PulseRingWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnim;
  late Animation<double> _opacityAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();

    _scaleAnim = Tween<double>(begin: 1.0, end: 1.6).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _opacityAnim = Tween<double>(begin: 0.6, end: 0.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.size * 1.6,
      height: widget.size * 1.6,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 파동 링
          AnimatedBuilder(
            animation: _controller,
            builder: (_, __) => Transform.scale(
              scale: _scaleAnim.value,
              child: Opacity(
                opacity: _opacityAnim.value,
                child: Container(
                  width: widget.size,
                  height: widget.size,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: widget.color, width: 2),
                  ),
                ),
              ),
            ),
          ),
          // 실제 자식 위젯
          widget.child,
        ],
      ),
    );
  }
}
