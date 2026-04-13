# ⏰ Pending Reminders

> 대표님이 "나중에 꼭 리마인드해 줘" 라고 요청하신 항목들.
> 매 Stage 전환 시점에 Claude 가 이 파일을 참조해 한 번씩 환기한다.

---

## 🔑 1. Anthropic API Key 설정

- **상태**: ⏸ 보류 (대표님 요청)
- **요청일**: 2026-04-13 (Stage 1 → Stage 2 전환 시점)
- **필요 이유**: 실제 `python src/main.py --demo` 실행으로 페르소나 동작
  검증 필요 (Premortem 1-3 "역할 뒤죽박죽" 대조 테스트)
- **어디서 발급**: https://console.anthropic.com → API Keys → Create Key
- **필요 크레딧**: 최소 $5 (Console → Plans & Billing)
- **설정 방법**: `cp .env.example .env` 후 `.env` 파일에 키 넣기
- **확인 명령**: `python -c "import os; print('OK' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET')"`

**🔔 리마인드 시점**:
- [ ] Stage 2 완료 시
- [ ] Stage 3 시작 전 (STT 추가 전에 Stage 1~2 실제 검증 권장)
- [ ] Stage 4 시작 전 (음성 들어가기 전에 텍스트부터 검증 필수)

---

## 사용법

Claude 는 각 Stage 종료 보고서 하단에 **"⏰ 대기 중인 리마인더"** 섹션을
자동으로 붙인다. 해결된 항목은 체크박스에 ✅ 표시하고 상태를 `✅ 완료`로
업데이트한다.
