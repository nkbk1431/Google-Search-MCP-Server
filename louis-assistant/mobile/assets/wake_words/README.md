# 웨이크워드 모델 설정 (sherpa-onnx KWS)

이 디렉터리에 모델 파일 5종이 있으면 "루이스" 온디바이스 감지가 활성화됩니다.
없으면 자동으로 **마이크 버튼 모드**로 폴백됩니다.

---

## 왜 중국어 모델인가?

sherpa-onnx에 **한국어 KWS 모델이 없습니다**.
"루이스"는 중국어 "路易斯"(lù yì sī)와 발음이 매우 유사하므로
**중국어 wenetspeech 모델**로 근사 감지합니다.

- 한국어 /루/ ≈ 중국어 lù (l + ù)
- 한국어 /이/ ≈ 중국어 yì (y + ì)
- 한국어 /스/ ≈ 중국어 sī (s + ī)

---

## 1단계: 모델 다운로드

### 권장 모델 (15.3MB, 모바일 최적화)

```
https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile.tar.bz2
```

Windows PowerShell에서 다운로드:
```powershell
cd louis-assistant\mobile\assets\wake_words

# 다운로드
Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile.tar.bz2" -OutFile "wenetspeech-mobile.tar.bz2"

# 압축 해제 (7-Zip 필요: https://www.7-zip.org)
# 7z x wenetspeech-mobile.tar.bz2
# 7z x wenetspeech-mobile.tar
```

또는 브라우저에서 직접 다운로드 후 7-Zip으로 해제.

---

## 2단계: 파일 배치 및 이름 변경

압축 해제하면 아래 파일들이 나옵니다:

```
sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile/
├── encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx   ← 이름 변경 필요
├── decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx   ← 이름 변경 필요
├── joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx    ← 이름 변경 필요
└── tokens.txt                                           ← 그대로 복사
```

이 디렉터리로 복사하면서 이름을 바꿔줍니다:

```powershell
$src = "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile"

Copy-Item "$src\encoder-*.onnx" "encoder.onnx"
Copy-Item "$src\decoder-*.onnx" "decoder.onnx"
Copy-Item "$src\joiner-*.onnx"  "joiner.onnx"
Copy-Item "$src\tokens.txt"     "tokens.txt"
```

`keywords.txt`는 이 디렉터리에 이미 있습니다. 수정 불필요.

---

## 최종 디렉터리 구조

```
assets/wake_words/
├── encoder.onnx      ← 모델 encoder (이름 변경된 것)
├── decoder.onnx      ← 모델 decoder (이름 변경된 것)
├── joiner.onnx       ← 모델 joiner  (이름 변경된 것)
├── tokens.txt        ← 토큰 사전
├── keywords.txt      ← 감지 키워드 (이미 있음, 수정 불필요)
└── README.md         ← 이 파일
```

---

## 3단계: APK 빌드

```powershell
cd mobile
flutter pub get
.\build_test_apk.ps1 192.168.x.x
```

---

## keywords.txt 내용 설명

```
l ù y ì s ī @루이스
l ú y ì s ī @루이스
l ù y í s ī @루이스
```

- 각 줄은 하나의 감지 패턴 (성조 변형 3가지)
- 공백으로 구분된 pinyin 음소 + `@표시이름`
- `@루이스` = 앱이 결과로 받는 키워드 이름
- 여러 줄 = OR 조건 (하나라도 맞으면 감지)

---

## 정확도 기대치

| 상황 | 예상 감지율 |
|------|-----------|
| 조용한 실내 | ~70-80% |
| 배경 소음 있음 | ~50-60% |
| 오탐지(오작동) | 낮음 |

중국어 모델이라 완벽하지 않습니다. 말이 안 될 경우 버튼을 사용하세요.

---

## 로그 확인

앱 실행 후 Android Logcat에서:
```
[WakeWord] sherpa-onnx KWS 시작 (wenetspeech)   ← 성공
[WakeWord] 감지: 루이스                           ← 감지됨
[WakeWord] 버튼 트리거 모드 (모델 없음)           ← 모델 없음/실패
```

---

## 대안: 더 큰 모델 (정확도 향상)

최신 zh-en 이중언어 모델 (32.9MB):
```
https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2
```
이 모델은 중국어 + 영어를 모두 지원하므로 "루이스" 발음에 더 잘 맞을 수 있습니다.
파일 이름 패턴은 동일하게 encoder/decoder/joiner.onnx로 변경하면 됩니다.
