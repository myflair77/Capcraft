# Capcraft 1.2.2

Windows 64비트용 업데이트 배포입니다. 내부 버전 번호와 릴리즈 태그는 `1.2.2`입니다.

## 다운로드

- 일반 사용자는 **Capcraft_Setup_v1.2.2.exe**를 다운로드해 설치하세요. (기존 v1.2 / v1.2.1을 삭제하지 않고 그대로 덮어쓰기 업그레이드 가능)
- 안내 페이지: https://capcraft-zeta.vercel.app/
- `SHA256SUMS.txt`에서 첨부파일의 SHA-256을 확인할 수 있습니다.

## v1.2.2 주요 변경 사항

- **앱 내 원클릭 업데이트 (`지금 업데이트`)**: 새 버전 알림 창에서 버튼 한 번으로 설치파일 다운로드(진행률 바·취소 지원) → SHA-256 무결성 검증 → 자동 설치 및 재실행을 지원합니다. *(v1.2.2 설치 이후 차기 버전부터 별도 브라우저 다운로드 없이 원클릭 업데이트 가능)*
- **v1.2.1 기능 포함**: Capcraft 실행창(미니 런처) 및 단일 인스턴스 실행, 캡처 직후 자동 클립보드 복사, 편집창 최초 표시 비율 자동 맞춤·좌우 폭맞춤, 상단 8개 도구 호버 미리보기·자동 활성화, 상단 `자석` 토글 버튼(`Alt + G`), `사용법` 목차 바로가기 및 업데이트 내역.

## 참고

OCR 모델을 포함하므로 설치파일과 설치 용량이 큽니다. 서명되지 않은 배포본이므로 Windows에서 게시자 경고를 표시할 수 있습니다. 보안 기능을 끄지 말고 공식 배포 출처와 해시를 확인하세요.

기존 사용자 설정(`.capcraft_settings.json`)과 캡처 기록(`.capcraft_history.json`)은 설치 폴더와 별도로 보관되어 업그레이드 후에도 그대로 유지됩니다.

전체 변경 이력은 [CHANGELOG.md](https://github.com/myflair77/Capcraft/blob/master/CHANGELOG.md)에서 확인할 수 있습니다.

## Code signing policy

현재 v1.2.2 파일은 미서명 상태입니다. SignPath Foundation 오픈소스 서명 지원 신청을 준비 중이며, 승인·인증서 발급·실제 서명은 완료되지 않았습니다.

- [Code signing policy](https://capcraft-zeta.vercel.app/signing.html)
- [개인정보 처리 안내](https://capcraft-zeta.vercel.app/privacy.html)
