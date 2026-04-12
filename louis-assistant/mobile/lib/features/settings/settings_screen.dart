import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants.dart';
import '../../core/services/api_client.dart';
import '../auth/auth_provider.dart';
import 'settings_provider.dart';

// ── 원격 선호도 Provider ─────────────────────────────────────────────

final _remotePrefsProvider = FutureProvider<Map<String, String>>((ref) async {
  try {
    return await ApiClient().getPreferences();
  } catch (_) {
    return {};
  }
});

final _usageProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    return await ApiClient().getUsage();
  } catch (_) {
    return {};
  }
});

// ── 설정 화면 ────────────────────────────────────────────────────────

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
          // ── 연결 설정 ──────────────────────────────────────────
          _SectionHeader(title: '서버 연결'),
          _ServerUrlTile(currentUrl: settings.serverUrl),

          // ── 음성 설정 ──────────────────────────────────────────
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

          // ── 알림 설정 ──────────────────────────────────────────
          _SectionHeader(title: '알림'),
          SwitchListTile(
            title: const Text('리마인더 알림'),
            value: settings.remindersEnabled,
            onChanged: (v) => ref.read(settingsProvider.notifier).setReminders(v),
            secondary: const Icon(Icons.notifications),
          ),

          // ── 사용자 선호도 ────────────────────────────────────────
          _SectionHeader(title: '학습된 선호도'),
          _PreferencesSection(),

          // ── 토큰 사용량 ──────────────────────────────────────────
          _SectionHeader(title: 'AI 사용량'),
          _UsageSection(),

          // ── 개인정보 ─────────────────────────────────────────────
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

          // ── 앱 정보 ──────────────────────────────────────────────
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
            onTap: () => _logout(context, ref),
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
    if (confirmed == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('대화 기록을 삭제했어요.')),
      );
    }
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    await ref.read(authProvider.notifier).logout();
  }
}

// ── 원격 선호도 섹션 ─────────────────────────────────────────────────

class _PreferencesSection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsAsync = ref.watch(_remotePrefsProvider);

    return prefsAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => ListTile(
        leading: const Icon(Icons.error_outline, color: Colors.grey),
        title: const Text('선호도를 불러오지 못했어요', style: TextStyle(color: Colors.grey)),
        subtitle: const Text('서버 연결을 확인해주세요'),
        trailing: IconButton(
          icon: const Icon(Icons.refresh),
          onPressed: () => ref.invalidate(_remotePrefsProvider),
        ),
      ),
      data: (prefs) {
        if (prefs.isEmpty) {
          return ListTile(
            leading: const Icon(Icons.psychology_outlined, color: Colors.grey),
            title: const Text('아직 학습된 선호도가 없어요',
                style: TextStyle(color: Colors.grey)),
            subtitle: const Text('루이스와 대화할수록 선호도가 쌓여요'),
            trailing: IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => ref.invalidate(_remotePrefsProvider),
            ),
          );
        }

        const labelMap = {
          'home_city': '자주 묻는 도시',
          'commute_mode': '선호 이동 수단',
          'wake_time': '자주 설정하는 알람',
          'music_genre': '음악 선호',
          'language': '번역 선호 언어',
          'currency_pair': '자주 쓰는 환율',
        };

        return Column(
          children: [
            ...prefs.entries.map((e) => ListTile(
                  dense: true,
                  leading: const Icon(Icons.circle, size: 8),
                  title: Text(labelMap[e.key] ?? e.key),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(e.value,
                          style: const TextStyle(
                              color: Colors.grey, fontSize: 13)),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, size: 18),
                        onPressed: () => _deletePreference(context, ref, e.key),
                      ),
                    ],
                  ),
                )),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: OutlinedButton.icon(
                onPressed: () => ref.invalidate(_remotePrefsProvider),
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('새로고침'),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _deletePreference(
      BuildContext context, WidgetRef ref, String key) async {
    try {
      await ApiClient().deletePreference(key);
      ref.invalidate(_remotePrefsProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('선호도를 삭제했어요.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('삭제에 실패했어요.')),
        );
      }
    }
  }
}

// ── 사용량 섹션 ────────────────────────────────────────────────────────

class _UsageSection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usageAsync = ref.watch(_usageProvider);
    final theme = Theme.of(context);

    return usageAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const ListTile(
        leading: Icon(Icons.bar_chart, color: Colors.grey),
        title: Text('사용량 조회 실패', style: TextStyle(color: Colors.grey)),
      ),
      data: (usage) {
        if (usage.isEmpty) return const SizedBox.shrink();

        final todayIn = (usage['today_tokens']?['in'] ?? 0) as int;
        final todayOut = (usage['today_tokens']?['out'] ?? 0) as int;
        final total = (usage['today_total'] ?? 0) as int;
        final limit = (usage['daily_limit'] ?? 100000) as int;
        final remaining = (usage['remaining'] ?? 0) as int;
        final monthlyCost = (usage['monthly_cost_usd'] ?? 0.0) as double;
        final progress = total / limit;

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.bar_chart,
                          color: theme.colorScheme.primary, size: 18),
                      const SizedBox(width: 8),
                      Text('오늘 사용량',
                          style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.primary)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(
                    value: progress.clamp(0.0, 1.0),
                    color: progress > 0.8 ? Colors.red : theme.colorScheme.primary,
                    backgroundColor: theme.colorScheme.surfaceVariant,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('$total 토큰 사용',
                          style: const TextStyle(fontSize: 13)),
                      Text('남은 토큰: $remaining',
                          style: const TextStyle(
                              fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                  const Divider(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _StatChip(label: '입력', value: '$todayIn'),
                      _StatChip(label: '출력', value: '$todayOut'),
                      _StatChip(
                          label: '이달 비용',
                          value: '\$${monthlyCost.toStringAsFixed(3)}'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label;
  final String value;
  const _StatChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        Text(label,
            style: const TextStyle(fontSize: 11, color: Colors.grey)),
      ],
    );
  }
}

// ── 공용 위젯 ──────────────────────────────────────────────────────────

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
