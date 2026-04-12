import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/services/widget_service.dart';

// ── 데이터 모델 ───────────────────────────────────────────────────

class TodoItem {
  final int id;
  final String content;
  final bool done;
  final DateTime createdAt;

  const TodoItem({
    required this.id,
    required this.content,
    required this.done,
    required this.createdAt,
  });

  TodoItem copyWith({bool? done}) => TodoItem(
        id: id,
        content: content,
        done: done ?? this.done,
        createdAt: createdAt,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'content': content,
        'done': done,
        'createdAt': createdAt.toIso8601String(),
      };

  factory TodoItem.fromJson(Map<String, dynamic> j) => TodoItem(
        id: j['id'] as int,
        content: j['content'] as String,
        done: j['done'] as bool,
        createdAt: DateTime.parse(j['createdAt'] as String),
      );
}

class ReminderItem {
  final int id;
  final String content;
  final DateTime triggerAt;
  final bool fired;

  const ReminderItem({
    required this.id,
    required this.content,
    required this.triggerAt,
    required this.fired,
  });

  ReminderItem copyWith({bool? fired}) => ReminderItem(
        id: id,
        content: content,
        triggerAt: triggerAt,
        fired: fired ?? this.fired,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'content': content,
        'triggerAt': triggerAt.toIso8601String(),
        'fired': fired,
      };

  factory ReminderItem.fromJson(Map<String, dynamic> j) => ReminderItem(
        id: j['id'] as int,
        content: j['content'] as String,
        triggerAt: DateTime.parse(j['triggerAt'] as String),
        fired: j['fired'] as bool,
      );
}

// ── Todo Notifier ─────────────────────────────────────────────────

class TodoNotifier extends StateNotifier<List<TodoItem>> {
  static const _key = 'todos_v1';
  int _nextId = 1;

  TodoNotifier() : super([]) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw != null) {
      final list = (jsonDecode(raw) as List)
          .map((e) => TodoItem.fromJson(e as Map<String, dynamic>))
          .toList();
      state = list;
      _nextId = list.isEmpty ? 1 : list.map((t) => t.id).reduce((a, b) => a > b ? a : b) + 1;
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(state.map((t) => t.toJson()).toList()));
  }

  void add(String content) {
    state = [
      TodoItem(id: _nextId++, content: content, done: false, createdAt: DateTime.now()),
      ...state,
    ];
    _save();
  }

  void toggle(int id) {
    state = [for (final t in state) if (t.id == id) t.copyWith(done: !t.done) else t];
    _save();
  }

  void remove(int id) {
    state = state.where((t) => t.id != id).toList();
    _save();
  }

  /// Agent가 도구를 통해 추가한 할일을 반영합니다.
  void syncFromAgent(String content) => add(content);
}

// ── Reminder Notifier ─────────────────────────────────────────────

class ReminderNotifier extends StateNotifier<List<ReminderItem>> {
  static const _key = 'reminders_v1';
  int _nextId = 1;

  ReminderNotifier() : super([]) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw != null) {
      final list = (jsonDecode(raw) as List)
          .map((e) => ReminderItem.fromJson(e as Map<String, dynamic>))
          .toList();
      state = list;
      _nextId = list.isEmpty ? 1 : list.map((r) => r.id).reduce((a, b) => a > b ? a : b) + 1;
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(state.map((r) => r.toJson()).toList()));
  }

  void add(String content, DateTime triggerAt) {
    state = [
      ReminderItem(id: _nextId++, content: content, triggerAt: triggerAt, fired: false),
      ...state,
    ];
    _save();
    _syncWidget();
  }

  void markFired(int id) {
    state = [for (final r in state) if (r.id == id) r.copyWith(fired: true) else r];
    _save();
    _syncWidget();
  }

  void remove(int id) {
    state = state.where((r) => r.id != id).toList();
    _save();
    _syncWidget();
  }

  /// 홈 화면 위젯에 가장 빠른 리마인더를 동기화합니다.
  void _syncWidget() {
    final upcoming = state
        .where((r) => !r.fired && r.triggerAt.isAfter(DateTime.now()))
        .toList()
      ..sort((a, b) => a.triggerAt.compareTo(b.triggerAt));

    final widgetText = upcoming.isEmpty
        ? null
        : '${upcoming.first.content} — '
          '${upcoming.first.triggerAt.month}/${upcoming.first.triggerAt.day} '
          '${upcoming.first.triggerAt.hour}:${upcoming.first.triggerAt.minute.toString().padLeft(2, '0')}';

    WidgetService().updateNextReminder(widgetText);
  }
}

// ── Providers ────────────────────────────────────────────────────

final todoProvider = StateNotifierProvider<TodoNotifier, List<TodoItem>>(
  (ref) => TodoNotifier(),
);

final reminderProvider = StateNotifierProvider<ReminderNotifier, List<ReminderItem>>(
  (ref) => ReminderNotifier(),
);
