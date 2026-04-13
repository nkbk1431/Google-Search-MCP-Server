import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

/// 네이티브 플랫폼 채널
/// Android/iOS 네이티브 기능: 전화, 문자, 지도, 카카오톡 실행
class LouisPlatformChannel {
  static const _channel = MethodChannel('com.yourname.louis/intents');

  static LouisPlatformChannel? _instance;
  factory LouisPlatformChannel() => _instance ??= LouisPlatformChannel._();
  LouisPlatformChannel._();

  /// Agent 응답에서 네이티브 인텐트를 파싱하여 실행합니다.
  Future<void> handleAgentToolCalls(List<Map<String, dynamic>> toolCalls) async {
    for (final call in toolCalls) {
      final result = call['result'] as String? ?? '';
      if (result.isEmpty) continue;
      try {
        final payload = jsonDecode(result) as Map<String, dynamic>;
        await _dispatch(payload);
      } catch (_) {
        // JSON이 아닌 경우 무시
      }
    }
  }

  Future<void> _dispatch(Map<String, dynamic> payload) async {
    final action = payload['action'] as String? ?? '';
    switch (action) {
      case 'PHONE_CALL':
        await makePhoneCall(payload['contact'] as String? ?? '');
      case 'SEND_SMS':
        await sendSms(
          contact: payload['contact'] as String? ?? '',
          message: payload['message'] as String? ?? '',
        );
      case 'OPEN_MAPS':
        await openMaps(
          origin: payload['origin'] as String? ?? '',
          destination: payload['destination'] as String? ?? '',
          mode: payload['mode'] as String? ?? 'transit',
        );
      case 'PLAY_MUSIC':
        await openMusicSearch(payload['query'] as String? ?? '');
      case 'OPEN_YOUTUBE':
        await openYouTube(payload['query'] as String? ?? '');
      case 'SMART_HOME_CONTROL':
        await smartHomeControl(payload);
      // Phase 12: 브라우저 열기 (쇼핑, 스포츠, 기차 등)
      case 'OPEN_BROWSER':
        await openBrowser(payload['url'] as String? ?? '');
    }
  }

  /// 전화 걸기
  Future<void> makePhoneCall(String contact) async {
    try {
      await _channel.invokeMethod('makePhoneCall', {'contact': contact});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 전화 실패: ${e.message}');
    }
  }

  /// 문자 보내기
  Future<void> sendSms({required String contact, required String message}) async {
    try {
      await _channel.invokeMethod('sendSms', {
        'contact': contact,
        'message': message,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 문자 실패: ${e.message}');
    }
  }

  /// 지도 앱 열기
  Future<void> openMaps({
    required String origin,
    required String destination,
    String mode = 'transit',
  }) async {
    try {
      await _channel.invokeMethod('openMaps', {
        'origin': origin,
        'destination': destination,
        'mode': mode,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 지도 열기 실패: ${e.message}');
    }
  }

  /// 음악 검색 (Spotify / 기본 플레이어)
  Future<void> openMusicSearch(String query) async {
    try {
      await _channel.invokeMethod('openMusicSearch', {'query': query});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 음악 실패: ${e.message}');
    }
  }

  /// YouTube 검색
  Future<void> openYouTube(String query) async {
    try {
      await _channel.invokeMethod('openYouTube', {'query': query});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 유튜브 실패: ${e.message}');
    }
  }

  /// 스마트홈 제어
  Future<void> smartHomeControl(Map<String, dynamic> payload) async {
    try {
      await _channel.invokeMethod('smartHomeControl', payload);
    } on PlatformException catch (e) {
      debugPrint('[Platform] 스마트홈 실패: ${e.message}');
    }
  }

  /// 카카오톡 메시지 전송
  Future<void> sendKakaoMessage({
    required String contact,
    required String message,
  }) async {
    try {
      await _channel.invokeMethod('sendKakaoMessage', {
        'contact': contact,
        'message': message,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 카카오톡 실패: ${e.message}');
    }
  }

  /// 브라우저 열기 (Phase 12: 쇼핑/스포츠/기차 등)
  /// url_launcher를 우선 사용하고, 실패 시 네이티브 채널로 폴백합니다.
  Future<void> openBrowser(String url) async {
    if (url.isEmpty) return;
    try {
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        return;
      }
    } catch (e) {
      debugPrint('[Platform] url_launcher 실패: $e');
    }
    // 폴백: 네이티브 채널
    try {
      await _channel.invokeMethod('openBrowser', {'url': url});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 브라우저 열기 실패: ${e.message}');
    }
  }
}

  /// 전화 걸기
  Future<void> makePhoneCall(String contact) async {
    try {
      await _channel.invokeMethod('makePhoneCall', {'contact': contact});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 전화 실패: ${e.message}');
    }
  }

  /// 문자 보내기
  Future<void> sendSms({required String contact, required String message}) async {
    try {
      await _channel.invokeMethod('sendSms', {
        'contact': contact,
        'message': message,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 문자 실패: ${e.message}');
    }
  }

  /// 지도 앱 열기
  Future<void> openMaps({
    required String origin,
    required String destination,
    String mode = 'transit',
  }) async {
    try {
      await _channel.invokeMethod('openMaps', {
        'origin': origin,
        'destination': destination,
        'mode': mode,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 지도 열기 실패: ${e.message}');
    }
  }

  /// 음악 검색 (Spotify / 기본 플레이어)
  Future<void> openMusicSearch(String query) async {
    try {
      await _channel.invokeMethod('openMusicSearch', {'query': query});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 음악 실패: ${e.message}');
    }
  }

  /// YouTube 검색
  Future<void> openYouTube(String query) async {
    try {
      await _channel.invokeMethod('openYouTube', {'query': query});
    } on PlatformException catch (e) {
      debugPrint('[Platform] 유튜브 실패: ${e.message}');
    }
  }

  /// 스마트홈 제어
  Future<void> smartHomeControl(Map<String, dynamic> payload) async {
    try {
      await _channel.invokeMethod('smartHomeControl', payload);
    } on PlatformException catch (e) {
      debugPrint('[Platform] 스마트홈 실패: ${e.message}');
    }
  }

  /// 카카오톡 메시지 전송
  Future<void> sendKakaoMessage({
    required String contact,
    required String message,
  }) async {
    try {
      await _channel.invokeMethod('sendKakaoMessage', {
        'contact': contact,
        'message': message,
      });
    } on PlatformException catch (e) {
      debugPrint('[Platform] 카카오톡 실패: ${e.message}');
    }
  }
}
