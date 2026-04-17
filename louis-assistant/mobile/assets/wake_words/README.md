# 웨이크워드 모델 (sherpa-onnx)

이 디렉터리에 모델 파일이 있으면 앱이 온디바이스 웨이크워드 감지를 시작합니다.
없으면 자동으로 **버튼 트리거 모드**로 폴백합니다.

## 필요한 파일 (5종)

```
assets/wake_words/
├── encoder.onnx       # zipformer2 encoder
├── decoder.onnx       # zipformer2 decoder
├── joiner.onnx        # zipformer2 joiner
├── tokens.txt         # 토큰 사전
└── keywords.txt       # 감지할 키워드 목록
```

## 모델 받기 — 방법 1: 사전 학습 모델 (빠름)

sherpa-onnx 공식 릴리즈에서 제공하는 KWS 모델 다운로드:

```bash
# k2-fsa 공식 릴리즈
# https://github.com/k2-fsa/sherpa-onnx/releases/tag/kws-models

# 중국어 wenetspeech 모델 (한국어 "루이스" 유사음 감지용)
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2
tar xvf sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2

# 파일 복사
cp sherpa-onnx-kws-*/encoder-*.onnx  encoder.onnx
cp sherpa-onnx-kws-*/decoder-*.onnx  decoder.onnx
cp sherpa-onnx-kws-*/joiner-*.onnx   joiner.onnx
cp sherpa-onnx-kws-*/tokens.txt      tokens.txt
```

## keywords.txt 작성 (한국어 "루이스")

`keywords.txt`는 감지할 단어의 **BPE 토큰 시퀀스**를 적습니다.
`@` 뒤는 앱이 감지 결과로 받는 표시 이름.

중국어 모델 사용 시 "루이스"를 유사 중국어 음절로 변환:
```
lu yi si @루이스
lu i s  @루이스
ru i s  @루이스
```

영어 모델 사용 시:
```
LOU IS @LOUIS
L U I S @LOUIS
```

여러 줄 = OR 조건 (하나라도 맞으면 감지)

## 방법 2: 직접 학습 (정확도 최고, 시간 소요)

한국어 "루이스" 전용 모델은 직접 학습 필요:

1. **데이터 수집**: 본인 목소리로 "루이스" 50~100회 녹음 (16kHz PCM)
2. **icefall 프레임워크 사용**:
   - https://github.com/k2-fsa/icefall
   - `egs/wenetspeech/KWS` 레시피 참고
3. **ONNX 변환** 후 이 디렉터리에 배치

학습 난이도: 중~상 (GPU 필요, 2~3일 소요)

## 테스트

모델 배치 후 APK 재빌드:
```powershell
cd mobile
flutter pub get
.\build_test_apk.ps1 192.168.0.10
```

앱 실행 후 로그:
- `[WakeWord] sherpa-onnx 온디바이스 감지 시작` → 성공
- `[WakeWord] 버튼 트리거 모드 (모델 없음)` → 모델 없음/실패 → 버튼 사용

## 참고

- 모델 크기: 3MB~30MB (APK에 포함됨)
- 지원 샘플레이트: 16kHz 고정
- CPU만 사용 (GPU 불필요)
- 공식 문서: https://k2-fsa.github.io/sherpa/onnx/kws/
