/// 리마인더 모델 (로컬 표시용)
class ReminderModel {
  final int id;
  final String content;
  final DateTime triggerAt;
  final bool fired;

  const ReminderModel({
    required this.id,
    required this.content,
    required this.triggerAt,
    required this.fired,
  });

  factory ReminderModel.fromJson(Map<String, dynamic> json) {
    return ReminderModel(
      id: json['id'] as int,
      content: json['content'] as String,
      triggerAt: DateTime.parse(json['trigger_at'] as String),
      fired: (json['fired'] as int) == 1,
    );
  }

  String get formattedTime {
    final h = triggerAt.hour;
    final m = triggerAt.minute;
    final ampm = h < 12 ? '오전' : '오후';
    final h12 = h % 12 == 0 ? 12 : h % 12;
    return '$ampm $h12시${m > 0 ? ' $m분' : ''}';
  }
}
