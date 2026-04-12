import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/constants.dart';
import '../../core/services/api_client.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final String? username;
  final String? error;

  const AuthState({
    this.status = AuthStatus.unknown,
    this.username,
    this.error,
  });

  AuthState copyWith({AuthStatus? status, String? username, String? error}) =>
      AuthState(
        status: status ?? this.status,
        username: username ?? this.username,
        error: error,
      );
}

class AuthNotifier extends StateNotifier<AuthState> {
  final _storage = const FlutterSecureStorage();
  final _api = ApiClient();

  AuthNotifier() : super(const AuthState()) {
    _checkToken();
  }

  Future<void> _checkToken() async {
    final token = await _storage.read(key: AppConstants.keyAccessToken);
    if (token != null) {
      state = state.copyWith(status: AuthStatus.authenticated);
    } else {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> login(String username, String password) async {
    state = state.copyWith(status: AuthStatus.unknown, error: null);
    try {
      await _api.login(username, password);
      state = AuthState(status: AuthStatus.authenticated, username: username);
    } on OfflineException {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: '인터넷 연결이 없어요.',
      );
    } on DioExceptionAdapter catch (e) {
      final msg = e.message ?? '로그인에 실패했어요.';
      state = state.copyWith(status: AuthStatus.unauthenticated, error: msg);
    } catch (_) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: '로그인에 실패했어요. 다시 시도해주세요.',
      );
    }
  }

  Future<void> register(String username, String password) async {
    state = state.copyWith(status: AuthStatus.unknown, error: null);
    try {
      await _api.register(username, password);
      state = AuthState(status: AuthStatus.authenticated, username: username);
    } on OfflineException {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: '인터넷 연결이 없어요.',
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: e.toString().contains('409') ? '이미 사용 중인 아이디예요.' : '회원가입에 실패했어요.',
      );
    }
  }

  Future<void> logout() async {
    await _api.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}

// Dio 예외 어댑터 (message 추출)
class DioExceptionAdapter implements Exception {
  final String? message;
  const DioExceptionAdapter(this.message);
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);
