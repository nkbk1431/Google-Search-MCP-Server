# 루이스(Louis) 개인비서 - Windows 개발 환경 설정 가이드

Python 3.12.13 + venv 기준으로 백엔드를 실행하고,
Flutter로 Android APK를 빌드하는 전체 과정을 설명합니다.

---

## 목차

1. [사전 설치 확인](#1-사전-설치-확인)
2. [가상환경 생성 (venv)](#2-가상환경-생성)
3. [프로젝트 설정](#3-프로젝트-설정)
4. [백엔드 실행](#4-백엔드-실행)
5. [Flutter 설치 (APK 빌드용)](#5-flutter-설치)
6. [Android APK 빌드](#6-android-apk-빌드)
7. [스마트폰 테스트](#7-스마트폰-테스트)
8. [VS Code 설정](#8-vs-code-설정)
9. [CUDA / GPU 설정](#9-cuda--gpu-설정)
10. [Windows 트러블슈팅](#10-windows-트러블슈팅)

---

## 1. 사전 설치 확인

아래 항목이 이미 설치돼 있어야 합니다.

### Python 3.12.13

```powershell
python --version
# Python 3.12.13 출력 확인
```

없으면 [python.org](https://www.python.org/downloads/) 에서 3.12.13 다운로드 후 설치.
설치 시 **"Add Python to PATH"** 반드시 체크.

### Git

```powershell
git --version
# 없으면: https://git-scm.com/download/win
```

### CUDA / cuDNN (이미 설치됨)

```powershell
nvcc --version        # CUDA 버전 확인
nvidia-smi            # GPU 상태 확인 (GTX 1050 Ti)
```

현재 프로젝트는 Claude API를 사용하므로 GPU가 필수는 아닙니다.
향후 로컬 LLM(llama.cpp 등) 연동 시 CUDA가 활용됩니다.

---

## 2. 가상환경 생성

Python 내장 `venv`를 사용합니다. Conda/Anaconda 불필요.

> **먼저 실행 (최초 1회) — PowerShell 스크립트 실행 허용**
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> `.venv\Scripts\activate` 실행 시 **"이 시스템에서 스크립트를 실행할 수 없습니다"** 오류가 나면
> 위 명령을 관리자 없이 일반 PowerShell에서 실행하면 해결됩니다.

```powershell
# 저장소 루트에서
cd $HOME\projects\LOUIS_APP

# 가상환경 생성 (최초 1회)
python -m venv .venv

# 활성화
.venv\Scripts\activate
# 프롬프트 앞에 (.venv) 표시 확인
```

> **매번 활성화하기 귀찮다면 — VS Code 자동 활성화**
> VS Code에서 Python 인터프리터로 `.venv`를 선택하면
> 터미널을 열 때 자동으로 활성화됩니다. (8번 참조)

### 가상환경 비활성화 (필요 시)

```powershell
deactivate
```

---

## 3. 프로젝트 설정

### 3-1. 저장소 클론

```powershell
cd $HOME
mkdir projects -ErrorAction SilentlyContinue
cd projects
git clone https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git
cd LOUIS_APP
```

### 3-2. 가상환경 활성화 및 의존성 설치

```powershell
.venv\Scripts\activate

# 의존성 설치
pip install -r backend\requirements.txt
```

> **lxml, numpy 빌드 에러 시:**
> ```powershell
> pip install --upgrade pip wheel
> pip install lxml numpy --only-binary :all:
> pip install -r backend\requirements.txt
> ```

### 3-3. 환경변수 설정

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

`.env` 필수 항목:

```ini
# Claude AI 응답 (필수)
ANTHROPIC_API_KEY=sk-ant-...
# → https://console.anthropic.com

# 날씨 기능 (권장)
OPENWEATHER_API_KEY=...
# → https://openweathermap.org/api (무료)

# 기본값 유지
APP_ENV=development
APP_SECRET_KEY=test-secret-key-change-in-production
DATABASE_URL=sqlite+aiosqlite:///./louis.db
```

---

## 4. 백엔드 실행

### 빠른 시작 스크립트

```powershell
.venv\Scripts\activate
cd backend
.\quick_start.ps1
```

실행 후 출력 예시:
```
========================================
 접속 정보
========================================
  PC 브라우저:  http://localhost:8000/docs
  스마트폰:     http://192.168.0.10:8000
  테스트 계정:  admin / louis1234
========================================
```

### 수동 실행

```powershell
.venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 테스트 실행

```powershell
.venv\Scripts\activate
cd backend
pytest tests/ -v --tb=short
```

---

## 5. Flutter 설치

### 5-1. Flutter SDK

1. [flutter.dev](https://flutter.dev/docs/get-started/install/windows) 에서 SDK zip 다운로드
2. `C:\flutter` 에 압축 해제
3. 시스템 환경변수 `Path`에 `C:\flutter\bin` 추가

```powershell
flutter --version   # 설치 확인
```

### 5-2. Android Studio

1. [developer.android.com/studio](https://developer.android.com/studio) 에서 다운로드
2. 설치 후 SDK Manager → Android 13 (API 33) 이상 설치

### 5-3. Flutter 환경 확인

```powershell
flutter doctor
# Flutter SDK ✓, Android toolchain ✓ 확인
```

---

## 6. Android APK 빌드

### PowerShell 스크립트 사용

```powershell
cd mobile
.\build_test_apk.ps1 192.168.0.10   # quick_start.ps1이 알려준 IP 입력
```

### 수동 빌드

```powershell
cd mobile
flutter pub get
flutter build apk --debug --dart-define=BASE_URL=http://192.168.0.10:8000
```

APK 위치: `mobile\build\app\outputs\flutter-apk\app-debug.apk`

---

## 7. 스마트폰 테스트

### USB (adb)

```powershell
# 스마트폰: 개발자 옵션 → USB 디버깅 ON
adb devices
adb install mobile\build\app\outputs\flutter-apk\app-debug.apk
```

### 파일 전송

APK를 카카오톡/USB로 전송 후 스마트폰에서 직접 설치.
스마트폰 설정 → 보안 → **출처를 알 수 없는 앱 허용** 필요.

### 연결 조건

- PC와 스마트폰이 **같은 Wi-Fi** 연결
- Windows 방화벽 8000포트 허용 (quick_start.ps1이 자동 설정)

---

## 8. VS Code 설정

### 권장 확장

```
ms-python.python
ms-python.pylance
dart-code.flutter
```

### Python 인터프리터 설정 (자동 활성화)

1. `Ctrl+Shift+P` → **Python: Select Interpreter**
2. `.venv\Scripts\python.exe` 선택
3. 이후 VS Code 터미널 열 때 자동으로 venv 활성화

### `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true
}
```

---

## 9. CUDA / GPU 설정

현재 GTX 1050 Ti + CUDA + cuDNN이 설치돼 있습니다.

### 현재 프로젝트에서의 역할

| 기능 | GPU 사용 여부 |
|------|-------------|
| Claude API 호출 | ❌ (클라우드 처리) |
| 날씨/일정/검색 도구 | ❌ |
| TTS (ElevenLabs) | ❌ |
| 향후 로컬 Whisper STT | ✅ GPU 가속 가능 |
| 향후 로컬 LLM | ✅ GPU 가속 가능 |

### 향후 로컬 AI 사용 시 (선택)

```powershell
# faster-whisper (로컬 STT, GPU 가속)
pip install faster-whisper

# llama-cpp-python (로컬 LLM, CUDA 빌드)
$env:CMAKE_ARGS="-DLLAMA_CUDA=on"
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

---

## 10. Windows 트러블슈팅

### `python` 명령을 찾지 못할 때

```powershell
# Python PATH 확인
where python
# 없으면 Python 설치 시 "Add to PATH" 누락 → 재설치
```

### `pip install` 중 빌드 에러

```powershell
# Visual C++ Build Tools 설치
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# "C++ build tools" 워크로드 선택

# 또는 미리 빌드된 바이너리만 사용
pip install lxml numpy --only-binary :all:
```

### PowerShell 스크립트 실행 에러

```powershell
# 관리자 PowerShell에서 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `adb devices`에 기기 미표시

```powershell
adb kill-server
adb start-server
adb devices
# 스마트폰에서 "USB 디버깅 허용" 팝업 → 허용
```

### 방화벽으로 스마트폰 접속 불가

```powershell
# 관리자 PowerShell에서
netsh advfirewall firewall add rule name="Louis Backend" dir=in action=allow protocol=TCP localport=8000
```

---

## Linux (Ubuntu) 사용자는?

```bash
conda activate louis   # Conda 환경 사용 중이라면
# 또는
source .venv/bin/activate   # venv 사용 시

cd backend
bash quick_start.sh
```
