# 루이스(Louis) 개인비서 - Windows 개발 환경 설정 가이드

Windows PC에서 Miniconda + Python 3.13.12 기준으로 백엔드를 실행하고,
Flutter로 Android 앱을 빌드하는 전체 과정을 설명합니다.

---

## 목차

1. [Python 버전 선택 이유](#1-python-버전-선택)
2. [Miniconda 설치](#2-miniconda-설치)
3. [Conda 가상환경 생성](#3-conda-가상환경-생성)
4. [프로젝트 클론 및 설정](#4-프로젝트-클론-및-설정)
5. [백엔드 실행](#5-백엔드-실행)
6. [Flutter 설치 (앱 빌드용)](#6-flutter-설치)
7. [Android APK 빌드](#7-android-apk-빌드)
8. [스마트폰 테스트](#8-스마트폰-테스트)
9. [VS Code 개발 환경 추천 설정](#9-vs-code-설정)
10. [Windows 트러블슈팅](#10-windows-트러블슈팅)

---

## 1. Python 버전 선택

**Python 3.13.12를 사용합니다.**

| 항목 | 3.13.12 | 비고 |
|------|---------|------|
| LangChain / LangGraph | ✅ | 공식 지원 |
| FastAPI / Pydantic | ✅ | 공식 지원 |
| pykrx (주식) | ✅ | numpy 3.13 호환 |
| passlib / bcrypt | ✅ | `bcrypt==4.3.0` + `passlib==1.7.4` 분리로 해결 |
| pvporcupine (웨이크워드) | ✅ | Python 3.x 지원 |

> Python 3.13에서 `crypt` 표준 모듈이 제거됐지만, 이 프로젝트는
> `bcrypt==4.3.0` + `passlib==1.7.4`를 별도 설치해 호환성 문제를 해결했습니다.

---

## 2. Miniconda 설치

### 2-1. 다운로드 및 설치

1. [Miniconda 공식 다운로드 페이지](https://docs.conda.io/en/latest/miniconda.html) 접속
2. **Miniconda3 Windows 64-bit** (`.exe`) 다운로드
3. 설치 시 옵션:
   - "Add Miniconda3 to my PATH" → **체크 권장** (또는 Anaconda Prompt 사용)
   - "Register Miniconda3 as my default Python 3.x" → 체크

### 2-2. 설치 확인

**PowerShell** 또는 **Anaconda Prompt** 열기:

```powershell
conda --version
# conda 24.x.x 출력되면 정상
```

> **PowerShell에서 conda를 찾지 못할 경우**:
> 시작 메뉴 → "Anaconda Prompt" 검색 후 사용하거나,
> PowerShell을 관리자로 열고 아래 실행:
> ```powershell
> conda init powershell
> # 새 PowerShell 창을 열면 적용됨
> ```

---

## 3. Conda 가상환경 생성

```powershell
# Python 3.12 환경 생성
conda create -n louis python=3.13.12 -y

# 환경 활성화
conda activate louis

# 확인
python --version
# Python 3.13.12 출력
```

> **매번 conda activate louis를 치기 싫다면:**
> VS Code에서 Python 인터프리터를 `louis` 환경으로 설정하면
> 터미널 열 때 자동으로 활성화됩니다. (아래 9번 참조)

---

## 4. 프로젝트 클론 및 설정

### 4-1. Git 설치 확인

```powershell
git --version
# 없으면: https://git-scm.com/download/win 에서 설치
```

### 4-2. 저장소 클론

```powershell
cd $HOME
mkdir projects
cd projects
git clone https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git
cd LOUIS_APP
```

### 4-3. 환경 변수 설정

```powershell
cd backend
Copy-Item .env.example .env
notepad .env
```

`.env` 파일에서 아래 항목을 설정합니다:

```ini
# 필수
ANTHROPIC_API_KEY=sk-ant-...          # https://console.anthropic.com
APP_SECRET_KEY=your-random-secret-32chars

# 날씨 기능 (권장)
OPENWEATHER_API_KEY=...               # https://openweathermap.org/api

# 기본값으로 두면 됨
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./louis.db
```

### 4-4. Python 패키지 설치

```powershell
# conda 환경이 활성화된 상태에서
conda activate louis
pip install -r requirements.txt
```

> **설치 중 에러가 나는 패키지가 있다면:**
> ```powershell
> # pykrx, lxml 등 빌드 도구가 필요한 경우
> conda install -c conda-forge lxml numpy -y
> pip install -r requirements.txt
> ```

---

## 5. 백엔드 실행

### 5-1. 빠른 시작 (PowerShell)

```powershell
conda activate louis
cd $HOME\projects\LOUIS_APP\backend
.\quick_start.ps1
```

또는 수동으로:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5-2. 실행 확인

브라우저에서 `http://localhost:8000/docs` 접속 → Swagger UI 확인

### 5-3. 테스트 계정

| 항목 | 값 |
|------|---|
| 아이디 | `admin` |
| 비밀번호 | `louis1234` |

---

## 6. Flutter 설치

### 6-1. Flutter SDK 다운로드

1. [Flutter 공식 사이트](https://flutter.dev/docs/get-started/install/windows) 접속
2. Flutter SDK zip 다운로드 후 압축 해제 (예: `C:\flutter`)
3. Path 환경변수에 `C:\flutter\bin` 추가:
   - 시작 → "환경 변수 편집" → Path → 새로 만들기 → `C:\flutter\bin`

### 6-2. Android Studio 설치

1. [Android Studio 다운로드](https://developer.android.com/studio)
2. 설치 후 SDK 설정:
   - Android Studio 실행 → SDK Manager → **Android SDK 설치**
   - Android 13 (API 33) 이상 설치

### 6-3. Flutter 환경 확인

```powershell
flutter doctor
```

모든 항목에 체크(✓)가 되면 준비 완료입니다.
`Flutter SDK`, `Android toolchain` 두 항목이 필수입니다.

---

## 7. Android APK 빌드

### 7-1. PowerShell 빌드 스크립트 사용

```powershell
cd $HOME\projects\LOUIS_APP\mobile
.\build_test_apk.ps1 192.168.0.10    # 백엔드 PC의 로컬 IP 입력
```

### 7-2. 수동 빌드

```powershell
cd $HOME\projects\LOUIS_APP\mobile
flutter pub get
flutter build apk --debug --dart-define=BASE_URL=http://192.168.0.10:8000
```

빌드된 APK 위치:
```
mobile\build\app\outputs\flutter-apk\app-debug.apk
```

---

## 8. 스마트폰 테스트

### 방법 A: USB (adb)

```powershell
# Android 개발자 옵션 → USB 디버깅 ON
adb devices          # 연결된 기기 확인
adb install mobile\build\app\outputs\flutter-apk\app-debug.apk
```

### 방법 B: 파일 전송

1. APK 파일을 카카오톡/이메일/USB로 스마트폰에 전송
2. 스마트폰 설정 → 보안 → "출처를 알 수 없는 앱 허용"
3. 전송한 APK 파일 클릭하여 설치

### 연결 확인

- 백엔드 PC와 스마트폰이 **같은 Wi-Fi**에 연결돼야 합니다
- 방화벽에서 8000 포트가 열려있어야 합니다:
  ```powershell
  # 관리자 PowerShell에서
  netsh advfirewall firewall add rule name="Louis Backend" dir=in action=allow protocol=TCP localport=8000
  ```

---

## 9. VS Code 설정

### 9-1. 권장 확장 프로그램

```
ms-python.python          # Python
ms-python.pylance         # 타입 힌트
dart-code.flutter         # Flutter
dart-code.dart-code       # Dart
ms-azuretools.vscode-docker  # Docker (선택)
```

### 9-2. Python 인터프리터 설정 (conda 자동 활성화)

1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. `conda (louis)` 환경 선택
3. 이후 VS Code 터미널은 자동으로 `conda activate louis` 상태

### 9-3. `.vscode/settings.json` (루트에 생성)

```json
{
  "python.defaultInterpreterPath": "C:\\Users\\[사용자명]\\miniconda3\\envs\\louis\\python.exe",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

---

## 10. Windows 트러블슈팅

### `uvicorn` 명령을 찾지 못하는 경우
```powershell
# conda 환경 활성화 확인
conda activate louis
# 명령 프롬프트 앞에 (louis) 표시 확인
uvicorn --version
```

### `pip install` 중 빌드 에러 (lxml, numpy 등)
```powershell
# Visual C++ Build Tools 설치
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 또는 conda에서 미리 빌드된 버전 설치
conda install -c conda-forge lxml numpy -y
```

### `adb devices`가 기기를 인식 못하는 경우
```powershell
# 스마트폰 USB 디버깅 확인
# 설정 → 개발자 옵션 → USB 디버깅 ON
# USB 연결 후 "이 컴퓨터에서 USB 디버깅 허용?" 팝업 → 허용
adb kill-server
adb start-server
adb devices
```

### PowerShell 스크립트 실행 정책 에러
```powershell
# 관리자 PowerShell에서 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows Defender가 APK 설치를 막는 경우
스마트폰 설정 → 보안 → "Google Play 프로텍트" → APK 설치 허용

---

## Linux (Ubuntu) 사용자는?

Ubuntu에서는 `quick_start.sh` / `build_test_apk.sh` 스크립트를 사용하세요.
자세한 내용은 루트의 `test_on_phone.sh` 파일을 참고하세요.

```bash
cd backend
bash quick_start.sh
```
