# System Internals — 시스템 깊이 학습 가이드

OS, 런타임, 시스템 라이브러리의 깊이를 공식 소스로 검증해 한국어로 정리한 학습 문서 모음.

## 구조

```
.
├── index.html              ← 최상위 진입점
├── assets/
│   ├── style.css           공통 스타일 (light/dark)
│   └── script.js           theme toggle + scroll
├── libc/                   libc 깊이 (62 chapters, 7 Parts)
│   ├── index.html          libc 허브
│   └── part1~7.html
└── pid/                    Linux 부팅과 PID 0/1/2 (57 sections)
    └── index.html
```

## GitHub Pages 배포

1. 이 디렉토리를 GitHub repo 의 root 에 둔다.
2. Settings → Pages → Source: main branch / root 또는 `/docs`.
3. 배포 URL 예시: `https://<USER>.github.io/<REPO>/`

## 로컬 미리보기

```bash
# Python 3
python3 -m http.server 8000
# 브라우저로 http://localhost:8000/ 열기
```

## 재빌드 (libc 의 md 수정 시)

`build.py` 가 변환 스크립트. 원본 md (`12_libc_internals.md`) 를 수정 후 실행하면 `libc/part1~7.html` 이 갱신된다.

```bash
python3 build.py
```
