import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/constants.dart';
import 'features/chat/chat_screen.dart';
import 'features/tasks/tasks_screen.dart';
import 'features/memo/memo_screen.dart';
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
      home: onboardingDone ? const HomeShell() : const OnboardingScreen(),
    );
  }
}

/// 메인 탭 네비게이션 셸
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 0;

  static const _tabs = [
    ChatScreen(),
    TasksScreen(),
    MemoScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _tabs,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: '루이스',
          ),
          NavigationDestination(
            icon: Icon(Icons.check_box_outlined),
            selectedIcon: Icon(Icons.check_box),
            label: '할일',
          ),
          NavigationDestination(
            icon: Icon(Icons.note_alt_outlined),
            selectedIcon: Icon(Icons.note_alt),
            label: '메모',
          ),
        ],
      ),
    );
  }
}
