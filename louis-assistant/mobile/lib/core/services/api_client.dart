import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants.dart';
import 'connectivity_service.dart';

/// 네트워크 없음 예외
class OfflineException implements Exception {
  const OfflineException();
  @override
  String toString() => '인터넷 연결이 없어요.';
}

/// 루이스 백엔드 API 클라이언트
class ApiClient {
  static ApiClient? _instance;
  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  final _connectivity = ConnectivityService();

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
      // TODO: 리프레시 토큰으로 갱신 시도
    }
    handler.next(error);
  }

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
    await _storage.write(
      key: AppConstants.keyAccessToken,
      value: resp.data['access_token'],
    );
    await _storage.write(
      key: AppConstants.keyRefreshToken,
      value: resp.data['refresh_token'],
    );
  }
}

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
