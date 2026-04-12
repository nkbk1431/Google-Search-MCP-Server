import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants.dart';

class AppSettings {
  final String serverUrl;
  final bool wakeWordEnabled;
  final bool ttsEnabled;
  final double ttsRate;
  final bool remindersEnabled;

  const AppSettings({
    this.serverUrl = AppConstants.apiBaseUrl,
    this.wakeWordEnabled = true,
    this.ttsEnabled = true,
    this.ttsRate = 0.5,
    this.remindersEnabled = true,
  });

  AppSettings copyWith({
    String? serverUrl,
    bool? wakeWordEnabled,
    bool? ttsEnabled,
    double? ttsRate,
    bool? remindersEnabled,
  }) {
    return AppSettings(
      serverUrl: serverUrl ?? this.serverUrl,
      wakeWordEnabled: wakeWordEnabled ?? this.wakeWordEnabled,
      ttsEnabled: ttsEnabled ?? this.ttsEnabled,
      ttsRate: ttsRate ?? this.ttsRate,
      remindersEnabled: remindersEnabled ?? this.remindersEnabled,
    );
  }
}

class SettingsNotifier extends StateNotifier<AppSettings> {
  SettingsNotifier() : super(const AppSettings()) {
    _load();
  }

  static const _keyServerUrl = 'settings_server_url';
  static const _keyWakeWord = 'settings_wake_word';
  static const _keyTts = 'settings_tts';
  static const _keyTtsRate = 'settings_tts_rate';
  static const _keyReminders = 'settings_reminders';

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    state = AppSettings(
      serverUrl: prefs.getString(_keyServerUrl) ?? AppConstants.apiBaseUrl,
      wakeWordEnabled: prefs.getBool(_keyWakeWord) ?? true,
      ttsEnabled: prefs.getBool(_keyTts) ?? true,
      ttsRate: prefs.getDouble(_keyTtsRate) ?? 0.5,
      remindersEnabled: prefs.getBool(_keyReminders) ?? true,
    );
  }

  Future<void> setServerUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyServerUrl, url);
    state = state.copyWith(serverUrl: url);
  }

  Future<void> setWakeWord(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyWakeWord, enabled);
    state = state.copyWith(wakeWordEnabled: enabled);
  }

  Future<void> setTts(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyTts, enabled);
    state = state.copyWith(ttsEnabled: enabled);
  }

  Future<void> setTtsRate(double rate) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_keyTtsRate, rate);
    state = state.copyWith(ttsRate: rate);
  }

  Future<void> setReminders(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyReminders, enabled);
    state = state.copyWith(remindersEnabled: enabled);
  }
}

final settingsProvider = StateNotifierProvider<SettingsNotifier, AppSettings>(
  (ref) => SettingsNotifier(),
);
