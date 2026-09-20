# Capcraft Windows 배포

## 구성

공식 안내 페이지: https://capcraft-zeta.vercel.app/ . 페이지 파일은 `distribution/`입니다. 로그인한 계정에서 `npx vercel deploy distribution --prod --yes --project capcraft`로 갱신합니다. `distribution/release.json`의 ready, installer_url, size, sha256은 검증된 공개 설치파일에 맞춰 갱신합니다. Vercel 페이지 배포와 GitHub master 푸시는 별개입니다.

프로젝트 라이선스는 사용자 동의에 따라 GPL-3.0-only로 설정했습니다. LICENSE와 SOURCE_CODE.md를 함께 배포합니다. 설치용 아이콘은 `scripts/prepare_release_resources.py`가 앱과 같은 카메라 SVG에서 16~256px ICO로 생성합니다. guide.html은 `_guide_resource` 모듈로 압축하여 PYZ에 포함되므로 설치 폴더에 별도 HTML 파일이 생기지 않습니다(추출 방지/비공개 소스 기능이 아님).

- 설치파일: GitHub Releases (`myflair77/Capcraft`). 설치파일을 Git 소스에 넣지 않습니다.
- 최신 버전 안내: `distribution/latest.json`, 현재 `master` 브랜치의 공개 raw HTTPS 주소.
- 앱 버전과 확인 주소: `app_version.py`.
- 실행 5초 후 비동기 확인, 성공한 확인 기준 하루 한 번. 오프라인 실패는 자동 확인에서 조용히 무시합니다.
- 환경설정에서 자동 확인 해제 / 수동 확인 가능. 수동 확인은 건너뛰기·하루 제한을 무시합니다.
- 사용자가 눌러야 브라우저가 열립니다. 설치파일 자동 실행이나 백그라운드 설치는 하지 않습니다.
- 전송 내용은 버전 안내 파일 요청뿐입니다. 캡처 이미지/OCR 텍스트/설정은 업로드하지 않습니다. 호스팅 서비스에는 일반 HTTP 접속 정보(IP 등)가 보일 수 있습니다.
- 이미 배포된 앱에 업데이트 기능이 없었다면 새 설치파일을 한 번 직접 설치해야 합니다.

## 제작 및 공개 순서

1. 배포 라이선스를 결정합니다. PyQt6는 GPLv3 또는 상용 라이선스입니다. 소스가 GitHub에서 보인다는 것만으로 GPL 배포 요건이 자동 충족되지는 않습니다. 앱 라이선스, 의존성 고지 및 대응 소스 제공을 확인합니다.
2. `app_version.py` 버전, `installer_v1.2.iss`의 AppVersion과 출력 이름을 맞춥니다. 다음 버전에서도 **AppId를 바꾸지 않습니다**.
3. `build.bat`으로 개발용 빌드/테스트를 실행합니다. OCR 모델은 `python scripts/setup_ocr.py`로 설치 시점에 준비합니다(앱 사용 중 다운로드하지 않음).
4. Inno Setup의 `ISCC.exe installer_v1.2.iss`로 설치파일을 생성합니다. 결과는 `dist-dev/Installer/`입니다.
5. 별도 테스트 PC/Windows Sandbox에서 설치, 실행, OCR, 이미지 저장, 종료, 재설치를 확인합니다. 개인 캡처/설정 파일을 패키지에 넣지 않습니다.
6. 코드 변경을 커밋·푸시하고 해당 커밋에 `v1.2.0` 같은 태그로 GitHub Release 초안을 만듭니다. 설치파일과 SHA-256을 첨부합니다. GPL 배포라면 대응 소스와 의존성 라이선스도 함께 제공합니다.
7. 파일 검증 후 Release를 공개합니다. 마지막에 `distribution/latest.json`을 새 버전으로 갱신·푸시합니다. 설치파일을 먼저 제공해야 안내를 받은 사용자가 정상 다운로드할 수 있습니다.

예: 1.3.0 배포 시 안내 파일

```json
{"schema_version":1,"version":"1.3.0","download_page":"https://github.com/myflair77/Capcraft/releases/tag/v1.3.0","notes":"주요 변경 사항을 여기에 적습니다."}
```

미출시 버전, 베타 버전은 이 안정 버전 안내 파일에 게시하지 않습니다. 같은 버전 번호로 설치파일을 바꾸지 말고 오류 수정도 1.2.1처럼 버전을 올립니다. 앱을 끈 사용자에게는 알림이 가지 않습니다.

## 설치·업그레이드 주의

설정과 기록은 사용자 홈의 `.capcraft_settings.json`, `.capcraft_history.json`에 있으며 설치 폴더와 분리되어 있습니다. 업데이트 알림 선택은 `.capcraft_updates.json`입니다. 설치/제거에서 이 파일들을 삭제하지 않습니다. 첫 공개 전 기존 기록 백업과 재설치 테스트를 권장합니다.

코드 서명 인증서가 없으면 Windows가 알 수 없는 게시자/SmartScreen 경고를 표시할 수 있습니다. 서명 없는 배포를 숨기거나 사용자에게 보안 기능을 끄도록 안내하지 않습니다. Microsoft Store 등록은 별도 개발자 계정, 심사 및 패키지/서명 요건 확인이 필요합니다.

## 배포처 확장

GitHub Release 주소를 블로그·커뮤니티·홈페이지에서 공유하면 하나의 파일을 여러 곳에서 안내할 수 있습니다. Vercel은 다운로드 안내 페이지와 작은 버전 JSON 제공에 사용할 수 있고, 대용량 설치파일은 GitHub Releases에 계속 둘 수 있습니다. 업데이트 URL은 이미 설치된 앱에 들어 있으므로 현재 주소를 폐기하지 마세요. 다운로드 페이지 주소는 JSON에서 바꿀 수 있습니다.

## 공식 자료

- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases (파일당 2 GiB 미만)
- https://vercel.com/docs/deployments/overview
- https://www.riverbankcomputing.com/software/pyqt
- https://jrsoftware.org/isdl.php
- https://learn.microsoft.com/en-us/windows/apps/distribute-through-store/how-to-distribute-your-win32-app-through-microsoft-store
