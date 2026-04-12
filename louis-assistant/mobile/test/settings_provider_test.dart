import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:louis/features/settings/settings_provider.dart';
import 'package:louis/core/constants.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  ProviderContainer makeContainer() => ProviderContainer();

  // ── AppSettings 단위 테스트 ───────────────────────────

  group('AppSettings', () {
    test('기본값 확인', () {
      const settings = AppSettings();
      expect(settings.serverUrl, AppConstants.apiBaseUrl);
      expect(settings.wakeWordEnabled, isTrue);
      expect(settings.ttsEnabled, isTrue);
      expect(settings.ttsRate, 0.5);
      expect(settings.remindersEnabled, isTrue);
    });

    test('copyWith - serverUrl만 변경', () {
      const settings = AppSettings();
      final updated = settings.copyWith(serverUrl: 'https://custom.api.com');
      expect(updated.serverUrl, 'https://custom.api.com');
      expect(updated.wakeWordEnabled, settings.wakeWordEnabled);
      expect(updated.ttsRate, settings.ttsRate);
    });

    test('copyWith - wakeWordEnabled 변경', () {
      const settings = AppSettings(wakeWordEnabled: true);
      final updated = settings.copyWith(wakeWordEnabled: false);
      expect(updated.wakeWordEnabled, isFalse);
      expect(updated.ttsEnabled, isTrue); // 다른 값 유지
    });

    test('copyWith - ttsRate 변경', () {
      const settings = AppSettings(ttsRate: 0.5);
      final updated = settings.copyWith(ttsRate: 0.8);
      expect(updated.ttsRate, 0.8);
    });

    test('copyWith - ttsEnabled 변경', () {
      const settings = AppSettings(ttsEnabled: true);
      final updated = settings.copyWith(ttsEnabled: false);
      expect(updated.ttsEnabled, isFalse);
    });

    test('copyWith - remindersEnabled 변경', () {
      const settings = AppSettings(remindersEnabled: true);
      final updated = settings.copyWith(remindersEnabled: false);
      expect(updated.remindersEnabled, isFalse);
    });

    test('모든 필드 동시 변경', () {
      const settings = AppSettings();
      final updated = settings.copyWith(
        serverUrl: 'https://new.server.com',
        wakeWordEnabled: false,
        ttsEnabled: false,
        ttsRate: 0.9,
        remindersEnabled: false,
      );
      expect(updated.serverUrl, 'https://new.server.com');
      expect(updated.wakeWordEnabled, isFalse);
      expect(updated.ttsEnabled, isFalse);
      expect(updated.ttsRate, 0.9);
      expect(updated.remindersEnabled, isFalse);
    });
  });

  // ── SettingsNotifier 테스트 ───────────────────────────

  group('SettingsNotifier', () {
    test('초기 로드 후 기본값', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero); // _load() 완료 대기

      final settings = c.read(settingsProvider);
      expect(settings.serverUrl, AppConstants.apiBaseUrl);
      expect(settings.wakeWordEnabled, isTrue);
      expect(settings.ttsEnabled, isTrue);
    });

    test('setWakeWord false 저장 및 반영', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setWakeWord(false);
      expect(c.read(settingsProvider).wakeWordEnabled, isFalse);
    });

    test('setWakeWord 값이 SharedPreferences에 저장됨', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setWakeWord(false);

      // 새 컨테이너로 로드하면 저장된 값 복원
      final c2 = makeContainer();
      addTearDown(c2.dispose);
      await Future.delayed(const Duration(milliseconds: 50));
      expect(c2.read(settingsProvider).wakeWordEnabled, isFalse);
    });

    test('setTts false → true 토글', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setTts(false);
      expect(c.read(settingsProvider).ttsEnabled, isFalse);

      await c.read(settingsProvider.notifier).setTts(true);
      expect(c.read(settingsProvider).ttsEnabled, isTrue);
    });

    test('setTtsRate 변경', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setTtsRate(0.75);
      expect(c.read(settingsProvider).ttsRate, 0.75);
    });

    test('setServerUrl 변경', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setServerUrl('https://staging.louis.ai');
      expect(c.read(settingsProvider).serverUrl, 'https://staging.louis.ai');
    });

    test('setReminders false 저장', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setReminders(false);
      expect(c.read(settingsProvider).remindersEnabled, isFalse);
    });

    test('여러 설정 순차 변경', () async {
      final c = makeContainer();
      addTearDown(c.dispose);
      await Future.delayed(Duration.zero);

      await c.read(settingsProvider.notifier).setWakeWord(false);
      await c.read(settingsProvider.notifier).setTtsRate(0.6);
      await c.read(settingsProvider.notifier).setReminders(false);

      final s = c.read(settingsProvider);
      expect(s.wakeWordEnabled, isFalse);
      expect(s.ttsRate, 0.6);
      expect(s.remindersEnabled, isFalse);
    });
  });
}
