import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'memo_provider.dart';

/// 메모 목록 화면
/// - 텍스트 검색 + 스와이프 삭제 + 길게 눌러 수정
class MemoScreen extends ConsumerStatefulWidget {
  const MemoScreen({super.key});

  @override
  ConsumerState<MemoScreen> createState() => _MemoScreenState();
}

class _MemoScreenState extends ConsumerState<MemoScreen> {
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final allMemos = ref.watch(memoProvider);
    final memos = _query.isEmpty
        ? allMemos
        : ref.read(memoProvider.notifier).search(_query);

    return Scaffold(
      appBar: AppBar(
        title: const Text('메모'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: '새 메모',
            onPressed: () => _showAddSheet(context),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: TextField(
              controller: _searchController,
              onChanged: (v) => setState(() => _query = v),
              decoration: InputDecoration(
                hintText: '메모 검색...',
                prefixIcon: const Icon(Icons.search, size: 20),
                suffixIcon: _query.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _query = '');
                        },
                      )
                    : null,
                filled: true,
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
            ),
          ),
        ),
      ),
      body: memos.isEmpty
          ? _EmptyState(
              isSearching: _query.isNotEmpty,
              onAdd: () => _showAddSheet(context),
            )
          : ListView.separated(
              padding: const EdgeInsets.only(bottom: 80),
              itemCount: memos.length,
              separatorBuilder: (_, __) => const Divider(height: 1, indent: 16),
              itemBuilder: (ctx, i) => _MemoTile(
                memo: memos[i],
                onEdit: () => _showEditSheet(context, memos[i]),
              ),
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddSheet(context),
        icon: const Icon(Icons.edit_note),
        label: const Text('새 메모'),
      ),
    );
  }

  Future<void> _showAddSheet(BuildContext context) async {
    final controller = TextEditingController();
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _MemoInputSheet(
        title: '새 메모',
        controller: controller,
        onSave: (text) {
          ref.read(memoProvider.notifier).add(text);
          Navigator.pop(ctx);
        },
      ),
    );
  }

  Future<void> _showEditSheet(BuildContext context, MemoItem memo) async {
    final controller = TextEditingController(text: memo.content);
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _MemoInputSheet(
        title: '메모 수정',
        controller: controller,
        onSave: (text) {
          ref.read(memoProvider.notifier).update(memo.id, text);
          Navigator.pop(ctx);
        },
      ),
    );
  }
}

// ── 메모 타일 ────────────────────────────────────────────────────────

class _MemoTile extends ConsumerWidget {
  final MemoItem memo;
  final VoidCallback onEdit;

  const _MemoTile({required this.memo, required this.onEdit});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return Dismissible(
      key: Key('memo-${memo.id}'),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: Colors.red.withOpacity(0.85),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (_) async {
        return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('메모 삭제'),
            content: const Text('이 메모를 삭제할까요?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('취소'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('삭제'),
              ),
            ],
          ),
        );
      },
      onDismissed: (_) => ref.read(memoProvider.notifier).remove(memo.id),
      child: InkWell(
        onTap: onEdit,
        onLongPress: () {
          Clipboard.setData(ClipboardData(text: memo.content));
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('클립보드에 복사되었어요'), duration: Duration(seconds: 2)),
          );
        },
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                memo.content,
                style: const TextStyle(fontSize: 14, height: 1.5),
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 6),
              Text(
                _formatDate(memo.createdAt),
                style: TextStyle(
                  fontSize: 11,
                  color: theme.colorScheme.outline,
                ),
              ),
            ],
          ),
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
    if (diff.inDays < 7) return '${diff.inDays}일 전';
    return '${dt.year}.${dt.month.toString().padLeft(2, '0')}.${dt.day.toString().padLeft(2, '0')}';
  }
}

// ── 메모 입력 시트 ────────────────────────────────────────────────────

class _MemoInputSheet extends StatelessWidget {
  final String title;
  final TextEditingController controller;
  final ValueChanged<String> onSave;

  const _MemoInputSheet({
    required this.title,
    required this.controller,
    required this.onSave,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            autofocus: true,
            maxLines: 6,
            minLines: 3,
            decoration: const InputDecoration(
              hintText: '메모 내용을 입력하세요...',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              icon: const Icon(Icons.save_outlined),
              label: const Text('저장'),
              onPressed: () {
                final text = controller.text.trim();
                if (text.isNotEmpty) onSave(text);
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ── 빈 상태 ────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final bool isSearching;
  final VoidCallback onAdd;

  const _EmptyState({required this.isSearching, required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isSearching ? Icons.search_off : Icons.note_alt_outlined,
              size: 56,
              color: Colors.grey.shade300,
            ),
            const SizedBox(height: 16),
            Text(
              isSearching
                  ? '검색 결과가 없어요'
                  : '메모가 없어요\n루이스에게 "메모해줘"라고 말해보세요',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade500, height: 1.6),
            ),
            if (!isSearching) ...[
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: onAdd,
                icon: const Icon(Icons.add),
                label: const Text('직접 추가'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
