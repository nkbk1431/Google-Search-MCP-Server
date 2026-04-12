import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants.dart';
import '../chat/chat_screen.dart';

/// 온보딩 화면 - 앱 최초 실행 시 권한 요청 및 설정 안내
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _nextPage() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConstants.keyOnboardingDone, true);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const ChatScreen()),
    );
  }

  List<_OnboardingPage> get _pages => [
        _OnboardingPage(
          icon: Icons.record_voice_over,
          title: '루이스에게 말하세요',
          description: '"루이스"라고 부르면\n무엇이든 도와드립니다.',
          color: const Color(0xFF2563EB),
          onAction: null,
          actionLabel: null,
        ),
        _OnboardingPage(
          icon: Icons.mic,
          title: '마이크 권한 필요',
          description: '"루이스" 웨이크워드를 감지하고\n음성 명령을 듣기 위해\n마이크 권한이 필요합니다.',
          color: const Color(0xFF059669),
          onAction: _requestMicPermission,
          actionLabel: '마이크 권한 허용',
        ),
        _OnboardingPage(
          icon: Icons.notifications_active,
          title: '알림 권한 필요',
          description: '리마인더와 알람 알림을 받으려면\n알림 권한이 필요합니다.',
          color: const Color(0xFFD97706),
          onAction: _requestNotificationPermission,
          actionLabel: '알림 권한 허용',
        ),
        _OnboardingPage(
          icon: Icons.security,
          title: '개인정보 보호',
          description: '• 웨이크워드 감지는 기기에서만 처리\n• 음성은 명령 시에만 서버 전송\n• 30일 후 자동 삭제\n• 언제든 데이터 삭제 가능',
          color: const Color(0xFF7C3AED),
          onAction: null,
          actionLabel: null,
        ),
      ];

  Future<void> _requestMicPermission() async {
    await Permission.microphone.request();
    if (Permission.speech.isRestricted != null) {
      await Permission.speech.request();
    }
    _nextPage();
  }

  Future<void> _requestNotificationPermission() async {
    await Permission.notification.request();
    _nextPage();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLastPage = _currentPage == _pages.length - 1;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // 진행 표시
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                children: List.generate(
                  _pages.length,
                  (i) => Expanded(
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 2),
                      height: 4,
                      decoration: BoxDecoration(
                        color: i <= _currentPage
                            ? theme.colorScheme.primary
                            : theme.colorScheme.outlineVariant,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                ),
              ),
            ),

            // 페이지 내용
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (idx) => setState(() => _currentPage = idx),
                itemCount: _pages.length,
                itemBuilder: (_, i) => _PageContent(page: _pages[i]),
              ),
            ),

            // 하단 버튼
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
              child: Column(
                children: [
                  if (_pages[_currentPage].onAction != null)
                    FilledButton.icon(
                      onPressed: _pages[_currentPage].onAction,
                      icon: const Icon(Icons.check),
                      label: Text(_pages[_currentPage].actionLabel!),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size(double.infinity, 52),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                    ),
                  if (_pages[_currentPage].onAction != null) const SizedBox(height: 12),
                  isLastPage
                      ? FilledButton(
                          onPressed: _finish,
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(double.infinity, 52),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                          child: const Text('시작하기', style: TextStyle(fontSize: 16)),
                        )
                      : OutlinedButton(
                          onPressed: _nextPage,
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(double.infinity, 52),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                          child: const Text('다음', style: TextStyle(fontSize: 16)),
                        ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingPage {
  final IconData icon;
  final String title;
  final String description;
  final Color color;
  final VoidCallback? onAction;
  final String? actionLabel;

  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
    required this.onAction,
    required this.actionLabel,
  });
}

class _PageContent extends StatelessWidget {
  final _OnboardingPage page;
  const _PageContent({required this.page});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              color: page.color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(page.icon, size: 60, color: page.color),
          ),
          const SizedBox(height: 32),
          Text(
            page.title,
            style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          Text(
            page.description,
            style: const TextStyle(fontSize: 16, height: 1.6, color: Colors.grey),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
