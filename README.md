# System Internals — 시스템 깊이 학습 가이드

OS, 런타임, 시스템 라이브러리의 깊이를 공식 소스로 검증해 한국어로 정리한 학습 문서 모음.

## 🌐 Live Site

**https://hans9500.github.io/linux-internal-libc/**

### 직접 접근 가능한 페이지

| 문서 | URL |
|------|-----|
| 최상위 허브 | <https://hans9500.github.io/linux-internal-libc/> |
| libc 허브 | <https://hans9500.github.io/linux-internal-libc/libc/> |
| libc Part I — 기초 | <https://hans9500.github.io/linux-internal-libc/libc/part1.html> |
| libc Part II — libc 의 정체 | <https://hans9500.github.io/linux-internal-libc/libc/part2.html> |
| libc Part III — _start 부터 main 까지 | <https://hans9500.github.io/linux-internal-libc/libc/part3.html> |
| libc Part IV — malloc 의 깊이 | <https://hans9500.github.io/linux-internal-libc/libc/part4.html> |
| libc Part V — stdio 의 깊이 | <https://hans9500.github.io/linux-internal-libc/libc/part5.html> |
| libc Part VI — pthread 의 깊이 | <https://hans9500.github.io/linux-internal-libc/libc/part6.html> |
| libc Part VII — dynamic linker | <https://hans9500.github.io/linux-internal-libc/libc/part7.html> |
| Linux 부팅과 PID 0/1/2 | <https://hans9500.github.io/linux-internal-libc/pid/> |

## 📚 수록 문서

### 1. libc 깊이 이해 (62 chapters, 7 Parts)

C 라이브러리부터 언어 runtime 까지 — 30,359 줄 분량의 학습 문서.

- **Part I — 기초**: user-space 와 kernel-space 의 경계 (1~8장)
- **Part II — libc 의 정체**: 세 가지 일 (9~13장)
- **Part III — _start 부터 main 까지**: program startup 의 깊이 (14~22장)
- **Part IV — malloc 의 깊이**: 동적 메모리의 정체 (23~32장)
- **Part V — stdio 의 깊이**: 입출력의 정체 (33~42장)
- **Part VI — pthread 의 깊이**: 동시성의 정체 (43~52장)
- **Part VII — dynamic linker**: ld-linux.so 의 깊이 (53~62장)

검증 — glibc master, musl, Linux kernel 의 공식 소스와 대조.

### 2. Linux 부팅과 PID 0/1/2 (57 sections)

Linux 커널이 부팅되어 첫 사용자 프로세스가 실행되기까지의 흐름.

- main 함수의 정체와 freestanding 환경
- `start_kernel` 부터 `rest_init` 까지
- PID 0 (swapper), PID 1 (systemd), PID 2 (kthreadd) 의 정체
- `task_struct` 와 `struct pid` 의 분리 설계
- PID namespace 와 container 의 PID 1
- 단일 페이지, Stage 0~7 + Appendix

## 📁 디렉토리 구조

```
.
├── index.html              ← 최상위 진입점
├── assets/
│   ├── style.css           공통 스타일 (light/dark theme)
│   └── script.js           theme toggle + scroll active
├── libc/                   libc 깊이 (7 Parts)
│   ├── index.html
│   └── part1~7.html
└── pid/                    Linux 부팅과 PID
    └── index.html
```

## ✨ 기능

- 🌙 **light / dark 테마**: 시스템 설정 자동 감지 + 수동 토글
- 📋 **사이드바 + TOC**: 현재 섹션 자동 highlight, smooth scroll
- 🔗 **Part 간 navigation**: 상단/하단/사이드바 모두 지원
- 🎨 **syntax highlighting**: C, C++, Rust, Go, Bash, x86 asm 지원
- 📱 **반응형**: 모바일에서도 정상 표시

## 🛠️ 재빌드 (libc 의 md 수정 시)

`build.py` 가 변환 스크립트. 원본 md 를 수정 후 실행하면 `libc/part1~7.html` 갱신.

```bash
python3 build.py
```

## 📦 로컬 미리보기

```bash
# Python 3
python3 -m http.server 8000
# 브라우저로 http://localhost:8000/ 열기
```

## 📝 라이센스

학습 목적의 정리 문서. 인용 시 출처 명시 부탁드립니다.
