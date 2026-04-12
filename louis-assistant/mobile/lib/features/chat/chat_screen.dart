import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'chat_provider.dart';

/// 루이스 채팅 메인 화면
class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _scrollController = ScrollController();
  final _textController = TextEditingController();

  @override
  void dispose() {
    _scrollController.dispose();
    _textController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final chatNotifier = ref.read(chatProvider.notifier);

    // 메시지가 추가되면 스크롤
    ref.listen(chatProvider, (_, state) {
      if (state.messages.isNotEmpty) _scrollToBottom();
    });

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const CircleAvatar(
              radius: 16,
              backgroundColor: Colors.blueAccent,
              child: Text('L', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(width: 8),
            const Text('루이스'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: '대화 초기화',
            onPressed: () => chatNotifier.clearHistory(),
          ),
        ],
      ),
      body: Column(
        children: [
          // 상태 표시 배너
          _StatusBanner(state: chatState.voiceState),

          // 메시지 목록
          Expanded(
            child: chatState.messages.isEmpty
                ? _EmptyState(onMicPressed: () => chatNotifier.handleWakeWord())
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: chatState.messages.length,
                    itemBuilder: (ctx, i) => _MessageBubble(msg: chatState.messages[i]),
                  ),
          ),

          // 입력창
          _InputBar(
            controller: _textController,
            voiceState: chatState.voiceState,
            onSend: (text) {
              _textController.clear();
              chatNotifier.sendText(text);
            },
            onMic: () => chatNotifier.handleWakeWord(),
          ),
        ],
      ),
    );
  }
}

// ── 위젯 컴포넌트 ────────────────────────────────────────────────────

class _StatusBanner extends StatelessWidget {
  final VoiceState state;
  const _StatusBanner({required this.state});

  @override
  Widget build(BuildContext context) {
    if (state == VoiceState.idle) return const SizedBox.shrink();

    final (label, color) = switch (state) {
      VoiceState.listening => ('듣는 중...', Colors.green),
      VoiceState.processing => ('처리 중...', Colors.orange),
      VoiceState.speaking => ('말하는 중...', Colors.blue),
      VoiceState.idle => ('', Colors.transparent),
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 6),
      color: color.withOpacity(0.15),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
          const SizedBox(width: 8),
          Text(label, style: TextStyle(color: color, fontSize: 13)),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage msg;
  const _MessageBubble({required this.msg});

  @override
  Widget build(BuildContext context) {
    final isUser = msg.role == MessageRole.user;
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            const CircleAvatar(
              radius: 14,
              backgroundColor: Colors.blueAccent,
              child: Text('L', style: TextStyle(color: Colors.white, fontSize: 11)),
            ),
            const SizedBox(width: 6),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isUser
                    ? theme.colorScheme.primaryContainer
                    : theme.colorScheme.surfaceVariant,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(isUser ? 16 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 16),
                ),
              ),
              child: Text(msg.text, style: const TextStyle(fontSize: 15)),
            ),
          ),
          if (isUser) const SizedBox(width: 6),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final VoidCallback onMicPressed;
  const _EmptyState({required this.onMicPressed});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.mic_none, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('마이크 버튼을 눌러 대화를 시작하세요',
              style: TextStyle(color: Colors.grey, fontSize: 16)),
          const SizedBox(height: 8),
          const Text('"루이스"라고 불러도 됩니다',
              style: TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 24),
          FloatingActionButton(
            onPressed: onMicPressed,
            child: const Icon(Icons.mic),
          ),
        ],
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final VoiceState voiceState;
  final ValueChanged<String> onSend;
  final VoidCallback onMic;

  const _InputBar({
    required this.controller,
    required this.voiceState,
    required this.onSend,
    required this.onMic,
  });

  @override
  Widget build(BuildContext context) {
    final isIdle = voiceState == VoiceState.idle;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: isIdle,
                decoration: InputDecoration(
                  hintText: '메시지 입력...',
                  filled: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(24),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
                onSubmitted: onSend,
                textInputAction: TextInputAction.send,
              ),
            ),
            const SizedBox(width: 8),
            FloatingActionButton.small(
              onPressed: isIdle ? onMic : null,
              backgroundColor: isIdle ? null : Colors.grey,
              tooltip: '음성 입력',
              child: Icon(voiceState == VoiceState.listening ? Icons.stop : Icons.mic),
            ),
          ],
        ),
      ),
    );
  }
}
