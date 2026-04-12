import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'core/constants.dart';
import 'core/services/api_client.dart';
import 'core/services/notification_service.dart';
import 'features/auth/auth_provider.dart';
import 'features/auth/login_screen.dart';
import 'features/chat/chat_screen.dart';
import 'features/tasks/tasks_screen.dart';
import 'features/memo/memo_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'shared/theme.dart';

/// 백그라운드 FCM 메시지 핸들러 (최상위 함수 필수)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await NotificationService.show(
    id: message.hashCode,
    title: message.notification?.title ?? '루이스',
    body: message.notification?.body ?? '',
    payload: message.data['payload'],
  );
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase 초기화
  // firebase_options.dart는 `flutterfire configure` 명령으로 생성합니다.
  // ignore: avoid_catches_without_on_clauses
  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
    await _setupFcm();
  } catch (e) {
    // Firebase 설정 없을 때 graceful degradation (개발 환경)
    debugPrint('[Firebase] 초기화 스킵 (설정 없음): $e');
  }

  // 알림 서비스 초기화
  await NotificationService.initialize();

  final prefs = await SharedPreferences.getInstance();
  final onboardingDone = prefs.getBool(AppConstants.keyOnboardingDone) ?? false;

  runApp(
    ProviderScope(
      child: LouisApp(onboardingDone: onboardingDone),
    ),
  );
}

/// FCM 토큰 발급 및 서버 등록
Future<void> _setupFcm() async {
  final messaging = FirebaseMessaging.instance;

  // iOS 알림 권한 요청
  await messaging.requestPermission(
    alert: true,
    badge: true,
    sound: true,
  );

  // FCM 토큰 발급 및 서버 등록
  final token = await messaging.getToken();
  if (token != null) {
    await ApiClient().registerFcmToken(token);
    debugPrint('[FCM] 토큰 등록 완료: ${token.substring(0, 20)}...');
  }

  // 토큰 갱신 시 재등록
  messaging.onTokenRefresh.listen((newToken) {
    ApiClient().registerFcmToken(newToken);
  });

  // Foreground 메시지 → 로컬 알림으로 표시
  FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    final notification = message.notification;
    if (notification != null) {
      NotificationService.show(
        id: message.hashCode,
        title: notification.title ?? '루이스',
        body: notification.body ?? '',
        payload: message.data['payload'],
      );
    }
  });
}

class LouisApp extends ConsumerWidget {
  final bool onboardingDone;
  const LouisApp({super.key, required this.onboardingDone});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: '루이스',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      home: _buildHome(ref),
    );
  }

  Widget _buildHome(WidgetRef ref) {
    if (!onboardingDone) return const OnboardingScreen();

    final authState = ref.watch(authProvider);
    return switch (authState.status) {
      AuthStatus.unknown => const _SplashScreen(),
      AuthStatus.unauthenticated => const LoginScreen(),
      AuthStatus.authenticated => const HomeShell(),
    };
  }
}

/// 인증 상태 확인 중 표시되는 스플래시
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 40,
              backgroundColor: Colors.blueAccent,
              child: Text('L',
                  style: TextStyle(
                      fontSize: 40,
                      fontWeight: FontWeight.bold,
                      color: Colors.white)),
            ),
            SizedBox(height: 24),
            CircularProgressIndicator(),
          ],
        ),
      ),
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
