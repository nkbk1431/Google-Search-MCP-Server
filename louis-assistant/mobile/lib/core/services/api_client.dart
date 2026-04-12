import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants.dart';
import 'connectivity_service.dart';

/// 네트워크 없음 예외
class OfflineException implements Exception {
  const OfflineException();
  @override
  String toString() => '인터넷 연결이 없어요.';
}

/// 인증 만료 예외 (리프레시 토큰도 만료)
class AuthExpiredException implements Exception {
  const AuthExpiredException();
  @override
  String toString() => '로그인이 만료됐어요. 다시 로그인해주세요.';
}

/// 루이스 백엔드 API 클라이언트
class ApiClient {
  static ApiClient? _instance;
  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  final _connectivity = ConnectivityService();

  // 토큰 갱신 중 중복 요청 방지
  bool _isRefreshing = false;
  final List<_PendingRequest> _pendingQueue = [];

  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: '${AppConstants.apiBaseUrl}/api/${AppConstants.apiVersion}',
      connectTimeout: const Duration(seconds: AppConstants.apiTimeoutSeconds),
      receiveTimeout: const Duration(seconds: AppConstants.apiTimeoutSeconds),
    ));

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: _addAuthHeader,
        onError: _handleError,
      ),
    );
  }

  factory ApiClient() => _instance ??= ApiClient._();

  /// 싱글턴 리셋 (로그아웃 시 사용)
  static void reset() => _instance = null;

  Future<void> _addAuthHeader(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.read(key: AppConstants.keyAccessToken);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  Future<void> _handleError(
    DioException error,
    ErrorInterceptorHandler handler,
  ) async {
    if (error.response?.statusCode == 401) {
      // 리프레시 토큰 갱신 시도
      final retried = await _tryRefreshAndRetry(error);
      if (retried != null) {
        handler.resolve(retried);
        return;
      }
    }
    handler.next(error);
  }

  Future<Response?> _tryRefreshAndRetry(DioException original) async {
    final refreshToken = await _storage.read(key: AppConstants.keyRefreshToken);
    if (refreshToken == null) return null;

    if (_isRefreshing) {
      // 갱신 중 → 완료 후 재시도 대기
      final completer = _PendingRequest();
      _pendingQueue.add(completer);
      return completer.future;
    }

    _isRefreshing = true;
    try {
      // 리프레시 토큰으로 새 토큰 발급
      final resp = await _dio.post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(headers: {'Authorization': null}),
      );
      final newAccess = resp.data['access_token'] as String;
      final newRefresh = resp.data['refresh_token'] as String;

      await _storage.write(key: AppConstants.keyAccessToken, value: newAccess);
      await _storage.write(key: AppConstants.keyRefreshToken, value: newRefresh);

      // 대기 중인 요청 재개
      for (final pending in _pendingQueue) {
        pending.complete(null);
      }
      _pendingQueue.clear();

      // 원래 요청 재시도
      final opts = original.requestOptions;
      opts.headers['Authorization'] = 'Bearer $newAccess';
      return await _dio.fetch(opts);

    } on DioException {
      // 리프레시도 실패 → 모든 대기 요청 오류 처리
      for (final p in _pendingQueue) {
        p.completeError(const AuthExpiredException());
      }
      _pendingQueue.clear();
      // 저장된 토큰 삭제
      await _storage.delete(key: AppConstants.keyAccessToken);
      await _storage.delete(key: AppConstants.keyRefreshToken);
      return null;
    } finally {
      _isRefreshing = false;
    }
  }

  // ── Public API ─────────────────────────────────────────────────

  /// 루이스에게 말하기
  Future<ChatResponse> chat(String text, {String sessionId = 'default'}) async {
    if (_connectivity.isOffline) throw const OfflineException();

    final resp = await _dio.post('/chat', data: {
      'text': text,
      'session_id': sessionId,
    });
    return ChatResponse.fromJson(resp.data);
  }

  /// 로그인
  Future<void> login(String username, String password) async {
    if (_connectivity.isOffline) throw const OfflineException();

    final resp = await _dio.post(
      '/auth/token',
      data: 'username=$username&password=$password',
      options: Options(contentType: 'application/x-www-form-urlencoded'),
    );
    await _saveTokens(resp.data);
  }

  /// 신규 사용자 등록
  Future<void> register(String username, String password) async {
    if (_connectivity.isOffline) throw const OfflineException();

    final resp = await _dio.post('/auth/register', data: {
      'username': username,
      'password': password,
    });
    await _saveTokens(resp.data);
  }

  /// 로그아웃 (로컬 토큰 삭제 + FCM 해제)
  Future<void> logout() async {
    await unregisterFcmToken();
    await _storage.delete(key: AppConstants.keyAccessToken);
    await _storage.delete(key: AppConstants.keyRefreshToken);
    ApiClient.reset();
  }

  /// 토큰 사용량 조회
  Future<Map<String, dynamic>> getUsage() async {
    final resp = await _dio.get('/chat/usage');
    return (resp.data as Map<String, dynamic>);
  }

  /// 사용자 선호도 조회
  Future<Map<String, String>> getPreferences() async {
    final resp = await _dio.get('/preferences');
    return (resp.data['preferences'] as Map<String, dynamic>)
        .cast<String, String>();
  }

  /// 선호도 설정
  Future<void> setPreference(String key, String value) async {
    await _dio.put('/preferences/$key', queryParameters: {'value': value});
  }

  /// 선호도 삭제
  Future<void> deletePreference(String key) async {
    await _dio.delete('/preferences/$key');
  }

  /// FCM 토큰 서버에 등록
  Future<void> registerFcmToken(String fcmToken) async {
    if (_connectivity.isOffline) return; // 오프라인이면 조용히 스킵
    try {
      await _dio.post('/webhook/fcm/register', data: {'fcm_token': fcmToken});
    } catch (_) {
      // FCM 등록 실패는 비치명적 — 로그만 기록
      debugPrint('[ApiClient] FCM 토큰 등록 실패 (무시)');
    }
  }

  /// FCM 토큰 서버에서 삭제 (로그아웃 시)
  Future<void> unregisterFcmToken() async {
    try {
      await _dio.delete('/webhook/fcm/unregister');
    } catch (_) {}
  }

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    await _storage.write(
      key: AppConstants.keyAccessToken,
      value: data['access_token'] as String,
    );
    await _storage.write(
      key: AppConstants.keyRefreshToken,
      value: data['refresh_token'] as String,
    );
  }
}

// ── Helper: 대기 중 요청 ────────────────────────────────────────────

class _PendingRequest {
  Response? _result;
  Object? _error;
  bool _completed = false;
  final List<void Function()> _listeners = [];

  Future<Response?> get future async {
    if (_completed) {
      if (_error != null) throw _error!;
      return _result;
    }
    await Future.doWhile(() async {
      await Future.delayed(const Duration(milliseconds: 50));
      return !_completed;
    });
    if (_error != null) throw _error!;
    return _result;
  }

  void complete(Response? result) {
    _result = result;
    _completed = true;
  }

  void completeError(Object error) {
    _error = error;
    _completed = true;
  }
}

// ── Response Models ─────────────────────────────────────────────────

class ChatResponse {
  final String reply;
  final List<Map<String, dynamic>> toolCalls;
  final Map<String, int> tokens;

  ChatResponse({
    required this.reply,
    required this.toolCalls,
    required this.tokens,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      reply: json['reply'] as String,
      toolCalls: (json['tool_calls'] as List?)
              ?.cast<Map<String, dynamic>>() ??
          [],
      tokens: (json['tokens'] as Map?)?.cast<String, int>() ?? {},
    );
  }
}
