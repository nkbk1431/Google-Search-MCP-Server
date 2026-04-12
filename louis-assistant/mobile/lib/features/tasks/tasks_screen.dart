import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'tasks_provider.dart';

/// 할일(Todo) + 리마인더 통합 화면
/// 탭으로 구분: [할일] [리마인더]
class TasksScreen extends ConsumerWidget {
  const TasksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('할일 & 리마인더'),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.check_box_outlined), text: '할일'),
              Tab(icon: Icon(Icons.alarm), text: '리마인더'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            _TodoTab(),
            _ReminderTab(),
          ],
        ),
        floatingActionButton: _AddFab(),
      ),
    );
  }
}

// ── 할일 탭 ────────────────────────────────────────────────────────

class _TodoTab extends ConsumerWidget {
  const _TodoTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final todos = ref.watch(todoProvider);

    if (todos.isEmpty) {
      return _EmptyPlaceholder(
        icon: Icons.check_box_outlined,
        message: '할일이 없어요\n루이스에게 "장보기 목록에 우유 추가해줘"라고 말해보세요',
      );
    }

    final pending = todos.where((t) => !t.done).toList();
    final done = todos.where((t) => t.done).toList();

    return ListView(
      padding: const EdgeInsets.only(bottom: 80),
      children: [
        if (pending.isNotEmpty) ...[
          _ListHeader(title: '진행 중 (${pending.length})'),
          ...pending.map((t) => _TodoTile(todo: t)),
        ],
        if (done.isNotEmpty) ...[
          _ListHeader(title: '완료 (${done.length})'),
          ...done.map((t) => _TodoTile(todo: t)),
        ],
      ],
    );
  }
}

class _TodoTile extends ConsumerWidget {
  final TodoItem todo;
  const _TodoTile({required this.todo});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Dismissible(
      key: Key('todo-${todo.id}'),
      direction: DismissDirection.endToStart,
      background: _DismissBackground(color: Colors.red, icon: Icons.delete),
      onDismissed: (_) => ref.read(todoProvider.notifier).remove(todo.id),
      child: ListTile(
        leading: Checkbox(
          value: todo.done,
          onChanged: (_) => ref.read(todoProvider.notifier).toggle(todo.id),
          shape: const CircleBorder(),
        ),
        title: Text(
          todo.content,
          style: TextStyle(
            decoration: todo.done ? TextDecoration.lineThrough : null,
            color: todo.done ? Colors.grey : null,
          ),
        ),
        subtitle: Text(
          _formatDate(todo.createdAt),
          style: const TextStyle(fontSize: 11, color: Colors.grey),
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 1) return '방금';
    if (diff.inHours < 1) return '${diff.inMinutes}분 전';
    if (diff.inDays < 1) return '${diff.inHours}시간 전';
    return '${dt.month}/${dt.day}';
  }
}

// ── 리마인더 탭 ────────────────────────────────────────────────────

class _ReminderTab extends ConsumerWidget {
  const _ReminderTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reminders = ref.watch(reminderProvider);

    if (reminders.isEmpty) {
      return _EmptyPlaceholder(
        icon: Icons.alarm,
        message: '리마인더가 없어요\n"30분 뒤에 약 먹으라고 알려줘"라고 말해보세요',
      );
    }

    final upcoming = reminders.where((r) => !r.fired && r.triggerAt.isAfter(DateTime.now())).toList()
      ..sort((a, b) => a.triggerAt.compareTo(b.triggerAt));
    final fired = reminders.where((r) => r.fired || r.triggerAt.isBefore(DateTime.now())).toList();

    return ListView(
      padding: const EdgeInsets.only(bottom: 80),
      children: [
        if (upcoming.isNotEmpty) ...[
          _ListHeader(title: '예정 (${upcoming.length})'),
          ...upcoming.map((r) => _ReminderTile(reminder: r)),
        ],
        if (fired.isNotEmpty) ...[
          _ListHeader(title: '지난 알림 (${fired.length})'),
          ...fired.map((r) => _ReminderTile(reminder: r, faded: true)),
        ],
      ],
    );
  }
}

class _ReminderTile extends ConsumerWidget {
  final ReminderItem reminder;
  final bool faded;
  const _ReminderTile({required this.reminder, this.faded = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final dt = reminder.triggerAt;
    final timeStr = '${dt.month}/${dt.day} '
        '${dt.hour < 12 ? '오전' : '오후'} '
        '${dt.hour % 12 == 0 ? 12 : dt.hour % 12}시'
        '${dt.minute > 0 ? ' ${dt.minute}분' : ''}';

    return Dismissible(
      key: Key('reminder-${reminder.id}'),
      direction: DismissDirection.endToStart,
      background: _DismissBackground(color: Colors.orange, icon: Icons.delete),
      onDismissed: (_) => ref.read(reminderProvider.notifier).remove(reminder.id),
      child: ListTile(
        leading: Icon(
          Icons.alarm,
          color: faded ? Colors.grey : theme.colorScheme.primary,
        ),
        title: Text(
          reminder.content,
          style: TextStyle(color: faded ? Colors.grey : null),
        ),
        subtitle: Text(timeStr, style: const TextStyle(fontSize: 12)),
        trailing: faded
            ? const Icon(Icons.check_circle, color: Colors.green, size: 18)
            : null,
      ),
    );
  }
}

// ── FAB - 직접 추가 다이얼로그 ─────────────────────────────────────

class _AddFab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tabController = DefaultTabController.of(context);
    return FloatingActionButton.extended(
      onPressed: () => _showAddDialog(context, ref, tabController.index),
      icon: const Icon(Icons.add),
      label: const Text('추가'),
    );
  }

  Future<void> _showAddDialog(BuildContext context, WidgetRef ref, int tabIndex) async {
    final isTodo = tabIndex == 0;
    final controller = TextEditingController();
    DateTime? selectedTime;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => Padding(
          padding: EdgeInsets.fromLTRB(
            20, 20, 20, MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isTodo ? '할일 추가' : '리마인더 추가',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: controller,
                autofocus: true,
                decoration: InputDecoration(
                  hintText: isTodo ? '할일 내용' : '알림 내용',
                  border: const OutlineInputBorder(),
                ),
              ),
              if (!isTodo) ...[
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () async {
                    final picked = await showDateTimePicker(ctx);
                    if (picked != null) setState(() => selectedTime = picked);
                  },
                  icon: const Icon(Icons.access_time),
                  label: Text(
                    selectedTime == null
                        ? '시간 선택'
                        : '${selectedTime!.month}/${selectedTime!.day} '
                          '${selectedTime!.hour}:${selectedTime!.minute.toString().padLeft(2, '0')}',
                  ),
                ),
              ],
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () {
                    final text = controller.text.trim();
                    if (text.isEmpty) return;
                    if (isTodo) {
                      ref.read(todoProvider.notifier).add(text);
                    } else {
                      final time = selectedTime ?? DateTime.now().add(const Duration(minutes: 30));
                      ref.read(reminderProvider.notifier).add(text, time);
                    }
                    Navigator.pop(ctx);
                  },
                  child: const Text('추가'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<DateTime?> showDateTimePicker(BuildContext context) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (date == null || !context.mounted) return null;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );
    if (time == null) return null;
    return DateTime(date.year, date.month, date.day, time.hour, time.minute);
  }
}

// ── 공용 위젯 ──────────────────────────────────────────────────────

class _ListHeader extends StatelessWidget {
  final String title;
  const _ListHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.primary,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _EmptyPlaceholder extends StatelessWidget {
  final IconData icon;
  final String message;
  const _EmptyPlaceholder({required this.icon, required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 56, color: Colors.grey.shade300),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade500, height: 1.6),
            ),
          ],
        ),
      ),
    );
  }
}

class _DismissBackground extends StatelessWidget {
  final Color color;
  final IconData icon;
  const _DismissBackground({required this.color, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.only(right: 20),
      color: color.withOpacity(0.85),
      child: Icon(icon, color: Colors.white),
    );
  }
}
