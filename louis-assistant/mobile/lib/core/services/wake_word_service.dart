import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

/// 웨이크워드 감지 서비스 (sherpa-onnx KWS + 버튼 폴백)
///
/// 동작 모드:
///   1. sherpa-onnx: assets/wake_words/ 에 모델 5종이 있으면 온디바이스 감지
///      - 모델: wenetspeech KWS (중국어 음소 → "루이스" 근사 감지)
///      - keywords.txt: `l ù y ì s ī @루이스` (pinyin 근사)
///   2. 버튼 트리거: 모델 없으면 자동 폴백, 마이크 버튼으로 활성화
///
/// 모델 준비 방법: assets/wake_words/README.md 참조
class WakeWordService extends ChangeNotifier {
  static const _sampleRate = 16000;
  static const _chunkSize = 1600; // 0.1초 @ 16kHz

  bool _isRunning = false;
  bool _sherpaActive = false;
  VoidCallback? _onWakeWord;

  sherpa.KeywordSpotter? _spotter;
  sherpa.OnlineStream? _onlineStream;

  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _audioSub;

  bool get isRunning => _isRunning;
  bool get sherpaActive => _sherpaActive;

  Future<void> start({required VoidCallback onWakeWord}) async {
    _onWakeWord = onWakeWord;

    final loaded = await _tryLoadModel();
    if (loaded) {
      _sherpaActive = true;
      await _startMicStream();
      debugPrint('[WakeWord] sherpa-onnx KWS 시작 (wenetspeech)');
    } else {
      _sherpaActive = false;
      debugPrint('[WakeWord] 버튼 트리거 모드 (모델 없음)');
    }

    _isRunning = true;
    notifyListeners();
  }

  /// 마이크 버튼 또는 외부 이벤트로 직접 활성화
  void trigger() => _onWakeWord?.call();

  Future<void> pause() async {
    await _audioSub?.cancel();
    _audioSub = null;
    if (_sherpaActive) {
      try { await _recorder.stop(); } catch (_) {}
    }
    _isRunning = false;
    notifyListeners();
  }

  Future<void> resume() async {
    if (_sherpaActive) await _startMicStream();
    _isRunning = true;
    notifyListeners();
  }

  @override
  Future<void> dispose() async {
    await _audioSub?.cancel();
    try { await _recorder.dispose(); } catch (_) {}
    _onlineStream?.free();
    _spotter?.free();
    _onlineStream = null;
    _spotter = null;
    _isRunning = false;
    super.dispose();
  }

  // ── 모델 로드 ─────────────────────────────────────────────────────

  Future<bool> _tryLoadModel() async {
    try {
      final dir = await getApplicationSupportDirectory();
      final modelDir = Directory('${dir.path}/wake_word_model');

      // 최초 실행 시 assets → app support 디렉터리로 복사
      if (!modelDir.existsSync()) {
        modelDir.createSync(recursive: true);
      }

      final encoder  = await _copyAsset('encoder.onnx',  modelDir);
      final decoder  = await _copyAsset('decoder.onnx',  modelDir);
      final joiner   = await _copyAsset('joiner.onnx',   modelDir);
      final tokens   = await _copyAsset('tokens.txt',    modelDir);
      final keywords = await _copyAsset('keywords.txt',  modelDir);

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
          numThreads: 2,
          debug: false,
        ),
        keywordsFile: keywords!,
        // 키워드 앞뒤 묵음 임계값 (낮을수록 민감)
        keywordsScore: 1.5,
        keywordsThreshold: 0.25,
        numTrailingBlanks: 1,
      );

      _spotter = sherpa.KeywordSpotter(config);
      _onlineStream = _spotter!.createStream();
      return true;
    } catch (e, st) {
      debugPrint('[WakeWord] 모델 로드 실패: $e\n$st');
      return false;
    }
  }

  /// assets/wake_words/{name} → {modelDir}/{name} 복사 (캐시)
  Future<String?> _copyAsset(String name, Directory modelDir) async {
    try {
      final destFile = File('${modelDir.path}/$name');
      // 이미 복사된 파일은 재사용
      if (!destFile.existsSync()) {
        final data = await rootBundle.load('assets/wake_words/$name');
        await destFile.writeAsBytes(data.buffer.asUint8List(), flush: true);
      }
      return destFile.path;
    } catch (_) {
      return null; // 파일 없으면 null → 폴백
    }
  }

  // ── 마이크 스트림 ─────────────────────────────────────────────────

  Future<void> _startMicStream() async {
    if (!await _recorder.hasPermission()) {
      debugPrint('[WakeWord] 마이크 권한 없음 → 버튼 모드로 폴백');
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
      onError: (e) => debugPrint('[WakeWord] 오디오 오류: $e'),
    );
  }

  void _onAudioChunk(Uint8List bytes) {
    if (_spotter == null || _onlineStream == null) return;

    final samples = _pcm16ToFloat(bytes);

    // 청크 단위로 나눠 처리 (0.1초씩)
    final total = samples.length;
    for (var offset = 0; offset < total; offset += _chunkSize) {
      final end = (offset + _chunkSize).clamp(0, total);
      final chunk = Float32List.sublistView(samples, offset, end);

      _onlineStream!.acceptWaveform(samples: chunk, sampleRate: _sampleRate);
      while (_spotter!.isReady(_onlineStream!)) {
        _spotter!.decode(_onlineStream!);
      }

      final result = _spotter!.getResult(_onlineStream!);
      if (result.keyword.isNotEmpty) {
        debugPrint('[WakeWord] 감지: ${result.keyword}');
        _spotter!.reset(_onlineStream!);
        _onWakeWord?.call();
        return; // 한 청크에서 감지 후 즉시 반환
      }
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
