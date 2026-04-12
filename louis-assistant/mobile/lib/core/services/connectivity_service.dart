import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

/// 네트워크 연결 상태를 감지하고 앱 전체에 알림을 제공합니다.
class ConnectivityService extends ChangeNotifier {
  static ConnectivityService? _instance;
  factory ConnectivityService() => _instance ??= ConnectivityService._();

  ConnectivityService._() {
    _init();
  }

  final _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _subscription;

  bool _isOnline = true;
  bool get isOnline => _isOnline;
  bool get isOffline => !_isOnline;

  // 오프라인 메시지 큐: 연결 복구 시 재전송
  final List<_QueuedMessage> _queue = [];
  List<_QueuedMessage> get queuedMessages => List.unmodifiable(_queue);

  Future<void> _init() async {
    final results = await _connectivity.checkConnectivity();
    _updateStatus(results);

    _subscription = _connectivity.onConnectivityChanged.listen(_updateStatus);
  }

  void _updateStatus(List<ConnectivityResult> results) {
    final wasOnline = _isOnline;
    _isOnline = results.any((r) =>
        r == ConnectivityResult.wifi ||
        r == ConnectivityResult.mobile ||
        r == ConnectivityResult.ethernet);

    if (!wasOnline && _isOnline) {
      // 연결 복구
      debugPrint('[Connectivity] 온라인 복구됨 — 큐 ${_queue.length}개 대기 중');
      notifyListeners();
    } else if (wasOnline && !_isOnline) {
      // 연결 끊김
      debugPrint('[Connectivity] 오프라인 전환됨');
      notifyListeners();
    }
  }

  /// 오프라인 중 보내지 못한 메시지를 큐에 저장합니다.
  void enqueue(String text, String sessionId) {
    _queue.add(_QueuedMessage(text: text, sessionId: sessionId));
    debugPrint('[Connectivity] 메시지 큐에 저장: "$text"');
  }

  /// 큐에서 메시지를 꺼내 반환합니다.
  List<_QueuedMessage> drainQueue() {
    final items = List<_QueuedMessage>.from(_queue);
    _queue.clear();
    return items;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}

class _QueuedMessage {
  final String text;
  final String sessionId;
  final DateTime queuedAt;

  _QueuedMessage({required this.text, required this.sessionId})
      : queuedAt = DateTime.now();
}
