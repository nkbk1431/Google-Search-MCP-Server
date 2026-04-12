import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_provider.dart';

/// 로그인 / 회원가입 통합 화면
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _loginFormKey = GlobalKey<FormState>();
  final _registerFormKey = GlobalKey<FormState>();

  final _loginUserCtrl = TextEditingController();
  final _loginPassCtrl = TextEditingController();
  final _regUserCtrl = TextEditingController();
  final _regPassCtrl = TextEditingController();
  final _regPassConfirmCtrl = TextEditingController();

  bool _obscureLogin = true;
  bool _obscureReg = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginUserCtrl.dispose();
    _loginPassCtrl.dispose();
    _regUserCtrl.dispose();
    _regPassCtrl.dispose();
    _regPassConfirmCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState.status == AuthStatus.unknown;
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 20),
          child: Column(
            children: [
              const SizedBox(height: 24),

              // ── 로고 ────────────────────────────────────────────
              CircleAvatar(
                radius: 40,
                backgroundColor: theme.colorScheme.primary,
                child: const Text(
                  'L',
                  style: TextStyle(
                    fontSize: 40,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                '루이스',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'AI 개인비서',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
              const SizedBox(height: 32),

              // ── 탭 바 ────────────────────────────────────────────
              TabBar(
                controller: _tabController,
                tabs: const [
                  Tab(text: '로그인'),
                  Tab(text: '회원가입'),
                ],
              ),
              const SizedBox(height: 24),

              // ── 오류 메시지 ──────────────────────────────────────
              if (authState.error != null)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline,
                          color: theme.colorScheme.error, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          authState.error!,
                          style: TextStyle(color: theme.colorScheme.error),
                        ),
                      ),
                    ],
                  ),
                ),

              // ── 폼 컨텐츠 ────────────────────────────────────────
              SizedBox(
                height: 300,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _loginForm(isLoading),
                    _registerForm(isLoading),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _loginForm(bool isLoading) {
    return Form(
      key: _loginFormKey,
      child: Column(
        children: [
          TextFormField(
            controller: _loginUserCtrl,
            decoration: const InputDecoration(
              labelText: '아이디',
              prefixIcon: Icon(Icons.person_outline),
              border: OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.next,
            validator: (v) => (v == null || v.isEmpty) ? '아이디를 입력해주세요.' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _loginPassCtrl,
            obscureText: _obscureLogin,
            decoration: InputDecoration(
              labelText: '비밀번호',
              prefixIcon: const Icon(Icons.lock_outline),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: Icon(_obscureLogin ? Icons.visibility_off : Icons.visibility),
                onPressed: () => setState(() => _obscureLogin = !_obscureLogin),
              ),
            ),
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _doLogin(),
            validator: (v) => (v == null || v.isEmpty) ? '비밀번호를 입력해주세요.' : null,
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: isLoading ? null : _doLogin,
              child: isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('로그인', style: TextStyle(fontSize: 16)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _registerForm(bool isLoading) {
    return Form(
      key: _registerFormKey,
      child: Column(
        children: [
          TextFormField(
            controller: _regUserCtrl,
            decoration: const InputDecoration(
              labelText: '아이디 (영문/숫자/밑줄, 3~32자)',
              prefixIcon: Icon(Icons.person_add_outlined),
              border: OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.next,
            validator: (v) {
              if (v == null || v.isEmpty) return '아이디를 입력해주세요.';
              if (v.length < 3) return '3자 이상 입력해주세요.';
              if (!RegExp(r'^[a-zA-Z0-9_]+$').hasMatch(v)) return '영문/숫자/밑줄만 사용 가능해요.';
              return null;
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _regPassCtrl,
            obscureText: _obscureReg,
            decoration: InputDecoration(
              labelText: '비밀번호 (8자 이상)',
              prefixIcon: const Icon(Icons.lock_outline),
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(
                icon: Icon(_obscureReg ? Icons.visibility_off : Icons.visibility),
                onPressed: () => setState(() => _obscureReg = !_obscureReg),
              ),
            ),
            textInputAction: TextInputAction.next,
            validator: (v) {
              if (v == null || v.length < 8) return '8자 이상 입력해주세요.';
              return null;
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _regPassConfirmCtrl,
            obscureText: _obscureReg,
            decoration: const InputDecoration(
              labelText: '비밀번호 확인',
              prefixIcon: Icon(Icons.lock_reset_outlined),
              border: OutlineInputBorder(),
            ),
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _doRegister(),
            validator: (v) =>
                v != _regPassCtrl.text ? '비밀번호가 일치하지 않아요.' : null,
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: isLoading ? null : _doRegister,
              child: isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('회원가입', style: TextStyle(fontSize: 16)),
            ),
          ),
        ],
      ),
    );
  }

  void _doLogin() {
    if (_loginFormKey.currentState?.validate() != true) return;
    ref.read(authProvider.notifier).login(
          _loginUserCtrl.text.trim(),
          _loginPassCtrl.text,
        );
  }

  void _doRegister() {
    if (_registerFormKey.currentState?.validate() != true) return;
    ref.read(authProvider.notifier).register(
          _regUserCtrl.text.trim(),
          _regPassCtrl.text,
        );
  }
}
