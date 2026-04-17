import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

/// 웨이크워드 감지 서비스
///
/// 동작 모드:
///   1. sherpa-onnx: assets/wake_words/ 에 모델이 있으면 온디바이스 감지
///   2. 버튼 트리거: 모델이 없으면 폴백. 마이크 버튼 누르면 trigger() 호출
///
/// 모델 파일 (필수 5종):
///   - encoder.onnx
///   - decoder.onnx
///   - joiner.onnx
///   - tokens.txt
///   - keywords.txt   (예: "ㄹ ㅜ ㅇ ㅣ ㅅ @루이스")
///
/// 모델 다운로드: docs/wake_word_setup.md 참조
class WakeWordService extends ChangeNotifier {
  static const _sampleRate = 16000;
  static const _assetPrefix = 'assets/wake_words/';

  bool _isRunning = false;
  bool _sherpaActive = false;
  VoidCallback? _onWakeWord;

  sherpa.KeywordSpotter? _spotter;
  sherpa.OnlineStream? _onlineStream;

  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _audioSub;

  bool get isRunning => _isRunning;

  /// sherpa-onnx 모델이 로드되어 온디바이스 감지가 동작 중인지
  bool get sherpaActive => _sherpaActive;

  Future<void> start({required VoidCallback onWakeWord}) async {
    _onWakeWord = onWakeWord;

    final loaded = await _tryLoadSherpa();
    if (loaded) {
      _sherpaActive = true;
      await _startMicStream();
      debugPrint('[WakeWord] sherpa-onnx 온디바이스 감지 시작');
    } else {
      _sherpaActive = false;
      debugPrint('[WakeWord] 버튼 트리거 모드 (모델 없음)');
    }

    _isRunning = true;
    notifyListeners();
  }

  /// 마이크 버튼/외부 이벤트로 직접 활성화
  void trigger() => _onWakeWord?.call();

  Future<void> pause() async {
    await _audioSub?.cancel();
    _audioSub = null;
    if (_sherpaActive) {
      try {
        await _recorder.stop();
      } catch (_) {}
    }
    _isRunning = false;
    notifyListeners();
  }

  Future<void> resume() async {
    if (_sherpaActive) {
      await _startMicStream();
    }
    _isRunning = true;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    await _audioSub?.cancel();
    try {
      await _recorder.dispose();
    } catch (_) {}
    _onlineStream?.free();
    _spotter?.free();
    _onlineStream = null;
    _spotter = null;
    _isRunning = false;
    super.dispose();
  }

  // ── sherpa-onnx 모델 로드 ──────────────────────────────────────────

  Future<bool> _tryLoadSherpa() async {
    try {
      final dir = await getApplicationSupportDirectory();

      final encoder = await _copyAsset('encoder.onnx', dir);
      final decoder = await _copyAsset('decoder.onnx', dir);
      final joiner = await _copyAsset('joiner.onnx', dir);
      final tokens = await _copyAsset('tokens.txt', dir);
      final keywords = await _copyAsset('keywords.txt', dir);

      if ([encoder, decoder, joiner, tokens, keywords].contains(null)) {
        return false;
      }

      sherpa.initBindings();

      final config = sherpa.KeywordSpotterConfig(
        model: sherpa.OnlineModelConfig(
          transducer: sherpa.OnlineTransducerModelConfig(
            encoder: encoder!,
            decoder: decoder!,
            joiner: joiner!,
          ),
          tokens: tokens!,
          modelType: 'zipformer2',
          numThreads: 1,
          debug: false,
        ),
        keywordsFile: keywords!,
      );

      _spotter = sherpa.KeywordSpotter(config);
      _onlineStream = _spotter!.createStream();
      return true;
    } catch (e, st) {
      debugPrint('[WakeWord] sherpa-onnx 초기화 실패: $e\n$st');
      return false;
    }
  }

  Future<String?> _copyAsset(String name, Directory dir) async {
    try {
      final data = await rootBundle.load('$_assetPrefix$name');
      final path = '${dir.path}/$name';
      final file = File(path);
      await file.writeAsBytes(data.buffer.asUint8List(), flush: true);
      return path;
    } catch (_) {
      return null;
    }
  }

  // ── 마이크 PCM 스트림 ──────────────────────────────────────────────

  Future<void> _startMicStream() async {
    if (!await _recorder.hasPermission()) {
      debugPrint('[WakeWord] 마이크 권한 없음 — 버튼 트리거로 폴백');
      _sherpaActive = false;
      return;
    }

    final stream = await _recorder.startStream(const RecordConfig(
      encoder: AudioEncoder.pcm16bits,
      sampleRate: _sampleRate,
      numChannels: 1,
    ));

    _audioSub = stream.listen(
      _onAudioChunk,
      onError: (e) => debugPrint('[WakeWord] 오디오 스트림 오류: $e'),
    );
  }

  void _onAudioChunk(Uint8List bytes) {
    if (_spotter == null || _onlineStream == null) return;

    final samples = _pcm16ToFloat(bytes);
    _onlineStream!.acceptWaveform(samples: samples, sampleRate: _sampleRate);

    while (_spotter!.isReady(_onlineStream!)) {
      _spotter!.decode(_onlineStream!);
    }

    final result = _spotter!.getResult(_onlineStream!);
    if (result.keyword.isNotEmpty) {
      debugPrint('[WakeWord] 감지: ${result.keyword}');
      _spotter!.reset(_onlineStream!);
      _onWakeWord?.call();
    }
  }

  Float32List _pcm16ToFloat(Uint8List bytes) {
    final view = ByteData.view(bytes.buffer, bytes.offsetInBytes, bytes.lengthInBytes);
    final samples = Float32List(bytes.lengthInBytes ~/ 2);
    for (var i = 0; i < samples.length; i++) {
      samples[i] = view.getInt16(i * 2, Endian.little) / 32768.0;
    }
    return samples;
  }
}
