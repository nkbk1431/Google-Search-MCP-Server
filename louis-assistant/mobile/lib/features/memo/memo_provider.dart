import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ── 데이터 모델 ────────────────────────────────────────────────────

class MemoItem {
  final int id;
  final String content;
  final DateTime createdAt;

  const MemoItem({
    required this.id,
    required this.content,
    required this.createdAt,
  });

  MemoItem copyWith({String? content}) => MemoItem(
        id: id,
        content: content ?? this.content,
        createdAt: createdAt,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'content': content,
        'createdAt': createdAt.toIso8601String(),
      };

  factory MemoItem.fromJson(Map<String, dynamic> j) => MemoItem(
        id: j['id'] as int,
        content: j['content'] as String,
        createdAt: DateTime.parse(j['createdAt'] as String),
      );
}

// ── Notifier ──────────────────────────────────────────────────────

class MemoNotifier extends StateNotifier<List<MemoItem>> {
  static const _key = 'memos_v1';
  int _nextId = 1;

  MemoNotifier() : super([]) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw != null) {
      final list = (jsonDecode(raw) as List)
          .map((e) => MemoItem.fromJson(e as Map<String, dynamic>))
          .toList();
      state = list;
      if (list.isNotEmpty) {
        _nextId = list.map((m) => m.id).reduce((a, b) => a > b ? a : b) + 1;
      }
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(state.map((m) => m.toJson()).toList()));
  }

  void add(String content) {
    if (content.trim().isEmpty) return;
    state = [
      MemoItem(id: _nextId++, content: content.trim(), createdAt: DateTime.now()),
      ...state,
    ];
    _save();
  }

  void update(int id, String newContent) {
    if (newContent.trim().isEmpty) return;
    state = [
      for (final m in state)
        if (m.id == id) m.copyWith(content: newContent.trim()) else m,
    ];
    _save();
  }

  void remove(int id) {
    state = state.where((m) => m.id != id).toList();
    _save();
  }

  List<MemoItem> search(String query) {
    if (query.trim().isEmpty) return state;
    final q = query.toLowerCase();
    return state.where((m) => m.content.toLowerCase().contains(q)).toList();
  }

  /// Agent가 도구를 통해 추가한 메모를 반영합니다.
  void syncFromAgent(String content) => add(content);
}

// ── Provider ──────────────────────────────────────────────────────

final memoProvider = StateNotifierProvider<MemoNotifier, List<MemoItem>>(
  (ref) => MemoNotifier(),
);
