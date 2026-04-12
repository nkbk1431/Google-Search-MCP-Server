import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/constants.dart';
import 'features/chat/chat_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'shared/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // TODO: Firebase 초기화 (firebase_options.dart 생성 후 활성화)
  // await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  final prefs = await SharedPreferences.getInstance();
  final onboardingDone = prefs.getBool(AppConstants.keyOnboardingDone) ?? false;

  runApp(
    ProviderScope(
      child: LouisApp(onboardingDone: onboardingDone),
    ),
  );
}

class LouisApp extends StatelessWidget {
  final bool onboardingDone;
  const LouisApp({super.key, required this.onboardingDone});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '루이스',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      home: onboardingDone ? const ChatScreen() : const OnboardingScreen(),
    );
  }
}
