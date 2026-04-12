import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants.dart';
import 'settings_provider.dart';

/// 루이스 설정 화면
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        children: [
          // ── 연결 설정 ──────────────────────────────────────
          _SectionHeader(title: '서버 연결'),
          _ServerUrlTile(currentUrl: settings.serverUrl),

          // ── 음성 설정 ──────────────────────────────────────
          _SectionHeader(title: '음성'),
          SwitchListTile(
            title: const Text('웨이크워드 사용'),
            subtitle: const Text('"루이스"라고 부르면 자동 활성화'),
            value: settings.wakeWordEnabled,
            onChanged: (v) => ref.read(settingsProvider.notifier).setWakeWord(v),
            secondary: const Icon(Icons.record_voice_over),
          ),
          SwitchListTile(
            title: const Text('음성 응답 (TTS)'),
            subtitle: const Text('루이스가 소리로 대답합니다'),
            value: settings.ttsEnabled,
            onChanged: (v) => ref.read(settingsProvider.notifier).setTts(v),
            secondary: const Icon(Icons.volume_up),
          ),
          ListTile(
            leading: const Icon(Icons.speed),
            title: const Text('말하기 속도'),
            subtitle: Slider(
              value: settings.ttsRate,
              min: 0.3,
              max: 1.0,
              divisions: 7,
              label: '${(settings.ttsRate * 100).round()}%',
              onChanged: (v) => ref.read(settingsProvider.notifier).setTtsRate(v),
            ),
          ),

          // ── 알림 설정 ──────────────────────────────────────
          _SectionHeader(title: '알림'),
          SwitchListTile(
            title: const Text('리마인더 알림'),
            value: settings.remindersEnabled,
            onChanged: (v) => ref.read(settingsProvider.notifier).setReminders(v),
            secondary: const Icon(Icons.notifications),
          ),

          // ── 개인정보 ────────────────────────────────────────
          _SectionHeader(title: '개인정보 및 데이터'),
          ListTile(
            leading: const Icon(Icons.delete_forever, color: Colors.red),
            title: const Text('대화 기록 삭제', style: TextStyle(color: Colors.red)),
            onTap: () => _confirmDeleteHistory(context, ref),
          ),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('개인정보처리방침'),
            trailing: const Icon(Icons.open_in_new, size: 16),
            onTap: () {/* TODO: URL 열기 */},
          ),

          // ── 앱 정보 ─────────────────────────────────────────
          _SectionHeader(title: '앱 정보'),
          ListTile(
            leading: const Icon(Icons.verified),
            title: const Text('버전'),
            trailing: Text(
              AppConstants.appVersion,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('로그아웃', style: TextStyle(color: Colors.red)),
            onTap: () => _logout(context),
          ),

          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Future<void> _confirmDeleteHistory(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('대화 기록 삭제'),
        content: const Text('모든 대화 기록을 삭제할까요? 이 작업은 되돌릴 수 없어요.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      // TODO: 대화 기록 삭제 API 호출
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('대화 기록을 삭제했어요.')),
        );
      }
    }
  }

  Future<void> _logout(BuildContext context) async {
    const storage = FlutterSecureStorage();
    await storage.deleteAll();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (context.mounted) {
      Navigator.of(context).pushNamedAndRemoveUntil('/', (route) => false);
    }
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.primary,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

class _ServerUrlTile extends ConsumerWidget {
  final String currentUrl;
  const _ServerUrlTile({required this.currentUrl});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: const Icon(Icons.dns),
      title: const Text('서버 URL'),
      subtitle: Text(
        currentUrl,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 12),
      ),
      trailing: const Icon(Icons.edit, size: 18),
      onTap: () async {
        final controller = TextEditingController(text: currentUrl);
        final newUrl = await showDialog<String>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('서버 URL 변경'),
            content: TextField(
              controller: controller,
              decoration: const InputDecoration(hintText: 'https://...'),
              keyboardType: TextInputType.url,
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('취소'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, controller.text),
                child: const Text('저장'),
              ),
            ],
          ),
        );
        if (newUrl != null && newUrl.isNotEmpty) {
          ref.read(settingsProvider.notifier).setServerUrl(newUrl);
        }
      },
    );
  }
}
