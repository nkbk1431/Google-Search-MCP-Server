/// 할일(Todo) 모델
class TodoModel {
  final int id;
  final String content;
  final bool done;
  final DateTime createdAt;

  const TodoModel({
    required this.id,
    required this.content,
    required this.done,
    required this.createdAt,
  });

  factory TodoModel.fromJson(Map<String, dynamic> json) {
    return TodoModel(
      id: json['id'] as int,
      content: json['content'] as String,
      done: json['done'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  TodoModel copyWith({bool? done}) {
    return TodoModel(
      id: id,
      content: content,
      done: done ?? this.done,
      createdAt: createdAt,
    );
  }
}
