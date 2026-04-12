import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'chat_provider.dart';
import '../settings/settings_screen.dart';
import '../../core/widgets/waveform_widget.dart';

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
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: '설정',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // 오프라인 배너
          if (chatState.isOffline) const _OfflineBanner(),

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

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: Colors.orange.shade700,
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      child: const Row(
        children: [
          Icon(Icons.wifi_off, color: Colors.white, size: 16),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '오프라인 상태입니다. 메시지는 연결 복구 시 자동으로 전송됩니다.',
              style: TextStyle(color: Colors.white, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

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

    final showWaveform =
        state == VoiceState.listening || state == VoiceState.speaking;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 6),
      color: color.withOpacity(0.12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (showWaveform)
            WaveformWidget(color: color, barCount: 5, height: 20)
          else
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
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment:
                isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser) ...[
                const CircleAvatar(
                  radius: 14,
                  backgroundColor: Colors.blueAccent,
                  child: Text('L',
                      style:
                          TextStyle(color: Colors.white, fontSize: 11)),
                ),
                const SizedBox(width: 6),
              ],
              Flexible(
                child: GestureDetector(
                  onLongPress: () {
                    Clipboard.setData(ClipboardData(text: msg.text));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('클립보드에 복사됐어요'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  },
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: msg.isOfflineNotice
                          ? Colors.orange.shade50
                          : isUser
                              ? theme.colorScheme.primaryContainer
                              : theme.colorScheme.surfaceVariant,
                      border: msg.isOfflineNotice
                          ? Border.all(color: Colors.orange.shade200)
                          : null,
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft: Radius.circular(isUser ? 16 : 4),
                        bottomRight: Radius.circular(isUser ? 4 : 16),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (msg.isOfflineNotice) ...[
                          const Icon(Icons.wifi_off,
                              size: 14, color: Colors.orange),
                          const SizedBox(width: 6),
                        ],
                        Flexible(
                          child: Text(
                            msg.text,
                            style: TextStyle(
                              fontSize: 15,
                              color: msg.isOfflineNotice
                                  ? Colors.orange.shade800
                                  : null,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              if (isUser) const SizedBox(width: 6),
            ],
          ),
          // 타임스탬프
          Padding(
            padding: EdgeInsets.only(
              left: isUser ? 0 : 40,
              right: isUser ? 6 : 0,
              top: 2,
            ),
            child: Text(
              _formatTime(msg.timestamp),
              style: TextStyle(
                fontSize: 10,
                color: theme.colorScheme.outline.withOpacity(0.6),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
    final m = dt.minute.toString().padLeft(2, '0');
    final ampm = dt.hour < 12 ? '오전' : '오후';
    return '$ampm $h:$m';
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
          const SizedBox(height: 8),
          const Text('또는 "루이스" 웨이크워드를 사용하세요',
              style: TextStyle(color: Colors.grey, fontSize: 11)),
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
            if (voiceState == VoiceState.listening)
              PulseRingWidget(
                color: Colors.green,
                size: 40,
                child: FloatingActionButton.small(
                  onPressed: onMic,
                  backgroundColor: Colors.green,
                  tooltip: '음성 입력 중지',
                  child: const Icon(Icons.stop, color: Colors.white),
                ),
              )
            else
              FloatingActionButton.small(
                onPressed: isIdle ? onMic : null,
                backgroundColor: isIdle ? null : Colors.grey,
                tooltip: '음성 입력',
                child: const Icon(Icons.mic),
              ),
          ],
        ),
      ),
    );
  }
}
