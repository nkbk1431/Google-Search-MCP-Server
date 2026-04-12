import 'package:flutter_test/flutter_test.dart';
import 'package:louis/core/services/api_client.dart';

void main() {
  // ── ChatResponse 단위 테스트 ──────────────────────────

  group('ChatResponse.fromJson', () {
    test('기본 응답 파싱', () {
      final json = {
        'reply': '안녕하세요! 무엇을 도와드릴까요?',
        'tool_calls': <Map<String, dynamic>>[],
        'tokens': {'in': 50, 'out': 30},
      };
      final response = ChatResponse.fromJson(json);
      expect(response.reply, '안녕하세요! 무엇을 도와드릴까요?');
      expect(response.toolCalls, isEmpty);
      expect(response.tokens['in'], 50);
      expect(response.tokens['out'], 30);
    });

    test('tool_calls null이면 빈 리스트', () {
      final json = {
        'reply': '결과입니다',
        'tool_calls': null,
        'tokens': <String, int>{},
      };
      final response = ChatResponse.fromJson(json);
      expect(response.toolCalls, isEmpty);
    });

    test('tokens null이면 빈 맵', () {
      final json = {
        'reply': '결과',
        'tool_calls': <dynamic>[],
        'tokens': null,
      };
      final response = ChatResponse.fromJson(json);
      expect(response.tokens, isEmpty);
    });

    test('tool_calls 데이터 파싱', () {
      final json = {
        'reply': '날씨를 조회했어요.',
        'tool_calls': [
          {
            'tool': 'get_weather',
            'result': '{"temp_now": 18.0, "condition": "맑음"}',
          }
        ],
        'tokens': {'in': 100, 'out': 60},
      };
      final response = ChatResponse.fromJson(json);
      expect(response.toolCalls, hasLength(1));
      expect(response.toolCalls[0]['tool'], 'get_weather');
    });

    test('reply가 빈 문자열도 허용', () {
      final json = {
        'reply': '',
        'tool_calls': <dynamic>[],
        'tokens': <String, int>{},
      };
      final response = ChatResponse.fromJson(json);
      expect(response.reply, '');
    });

    test('tokens 타입 캐스팅', () {
      final json = {
        'reply': '응답',
        'tool_calls': <dynamic>[],
        'tokens': <String, dynamic>{'in': 200, 'out': 100},
      };
      final response = ChatResponse.fromJson(json);
      expect(response.tokens['in'], isA<int>());
      expect(response.tokens['out'], isA<int>());
    });
  });

  // ── OfflineException 테스트 ───────────────────────────

  group('OfflineException', () {
    test('toString 메시지', () {
      const e = OfflineException();
      expect(e.toString(), contains('인터넷'));
    });

    test('Exception 구현', () {
      const e = OfflineException();
      expect(e, isA<Exception>());
    });

    test('catch로 잡힘', () {
      try {
        throw const OfflineException();
      } on OfflineException {
        // 정상적으로 잡혀야 합니다
        return;
      }
      fail('OfflineException이 잡히지 않았습니다');
    });

    test('const 생성자로 생성', () {
      const e1 = OfflineException();
      const e2 = OfflineException();
      expect(e1, isA<OfflineException>());
      expect(e2, isA<OfflineException>());
    });
  });

  // ── AuthExpiredException 테스트 ───────────────────────

  group('AuthExpiredException', () {
    test('toString 메시지', () {
      const e = AuthExpiredException();
      expect(e.toString(), contains('로그인'));
    });

    test('Exception 구현', () {
      const e = AuthExpiredException();
      expect(e, isA<Exception>());
    });

    test('catch로 잡힘', () {
      try {
        throw const AuthExpiredException();
      } on AuthExpiredException {
        return;
      }
      fail('AuthExpiredException이 잡히지 않았습니다');
    });

    test('OfflineException과 독립적', () {
      try {
        throw const AuthExpiredException();
      } on OfflineException {
        fail('AuthExpiredException이 OfflineException으로 잡혔습니다');
      } on AuthExpiredException {
        // 올바르게 잡혀야 합니다
      }
    });
  });

  // ── ApiClient 싱글턴 테스트 ───────────────────────────

  group('ApiClient 싱글턴', () {
    setUp(() {
      ApiClient.reset();
    });

    tearDown(() {
      ApiClient.reset();
    });

    test('동일 인스턴스 반환', () {
      final a = ApiClient();
      final b = ApiClient();
      expect(identical(a, b), isTrue);
    });

    test('reset 후 새 인스턴스 생성', () {
      final a = ApiClient();
      ApiClient.reset();
      final b = ApiClient();
      expect(identical(a, b), isFalse);
    });
  });
}
