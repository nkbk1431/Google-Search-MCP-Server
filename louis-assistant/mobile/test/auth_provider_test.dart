import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:louis/features/auth/auth_provider.dart';
import 'package:louis/core/services/api_client.dart';
import 'package:louis/core/constants.dart';

// ── 목 클래스 ─────────────────────────────────────────────

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}
class MockApiClient extends Mock implements ApiClient {}

// ── 테스트용 AuthNotifier (의존성 주입 가능) ─────────────

class _TestAuthNotifier extends AuthNotifier {
  final FlutterSecureStorage mockStorage;
  final ApiClient mockApi;

  _TestAuthNotifier(this.mockStorage, this.mockApi) : super._test();

  @override
  // ignore: invalid_use_of_protected_member
  FlutterSecureStorage get _storage => mockStorage;

  @override
  ApiClient get _api => mockApi;
}

// AuthNotifier에 테스트 생성자 노출이 어려우므로
// 동작 검증은 통합적으로 진행합니다.
// (실제 앱에서는 Provider override 패턴 사용)

void main() {
  // AuthState 단위 테스트
  group('AuthState', () {
    test('기본 상태는 unknown', () {
      const state = AuthState();
      expect(state.status, AuthStatus.unknown);
      expect(state.username, isNull);
      expect(state.error, isNull);
    });

    test('copyWith - status만 변경', () {
      const state = AuthState(status: AuthStatus.unknown, username: 'alice');
      final next = state.copyWith(status: AuthStatus.authenticated);
      expect(next.status, AuthStatus.authenticated);
      expect(next.username, 'alice'); // 유지
    });

    test('copyWith - error null 명시 시 null로 초기화', () {
      const state = AuthState(error: '이전 오류');
      final next = state.copyWith(error: null);
      expect(next.error, isNull);
    });

    test('copyWith - username 변경', () {
      const state = AuthState(username: 'old');
      final next = state.copyWith(username: 'new');
      expect(next.username, 'new');
    });

    test('authenticated 상태 생성', () {
      const state = AuthState(
        status: AuthStatus.authenticated,
        username: 'admin',
      );
      expect(state.status, AuthStatus.authenticated);
      expect(state.username, 'admin');
      expect(state.error, isNull);
    });

    test('unauthenticated + error 상태 생성', () {
      const state = AuthState(
        status: AuthStatus.unauthenticated,
        error: '비밀번호가 틀렸어요.',
      );
      expect(state.status, AuthStatus.unauthenticated);
      expect(state.error, '비밀번호가 틀렸어요.');
    });
  });

  // AuthStatus 열거형 테스트
  group('AuthStatus', () {
    test('3가지 상태 존재', () {
      expect(AuthStatus.values, hasLength(3));
      expect(AuthStatus.values, contains(AuthStatus.unknown));
      expect(AuthStatus.values, contains(AuthStatus.authenticated));
      expect(AuthStatus.values, contains(AuthStatus.unauthenticated));
    });
  });

  // DioExceptionAdapter 테스트
  group('DioExceptionAdapter', () {
    test('message 저장', () {
      const adapter = DioExceptionAdapter('로그인 실패');
      expect(adapter.message, '로그인 실패');
    });

    test('null message 허용', () {
      const adapter = DioExceptionAdapter(null);
      expect(adapter.message, isNull);
    });

    test('Exception 구현 확인', () {
      const adapter = DioExceptionAdapter('오류');
      expect(adapter, isA<Exception>());
    });
  });
}
