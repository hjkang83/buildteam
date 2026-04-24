# CLAUDE.md — 협업 가이드

## 프로젝트 개요

Data 기반 Multi-Agent 부동산 투자 자문 시스템 (KAIST IMMS MBA).
CFO·CSO·투자컨설턴트 3명의 AI C-suite가 실거래 데이터 기반으로 토론하며 투자 의사결정을 돕는다.

## 작업 방식

### 1. Forest First, Then Trees

- 새 작업을 시작할 때 **전체 그림(목표, 범위, 영향받는 파일)을 먼저 파악**한 뒤 세부 구현에 들어간다.
- 코드를 바로 작성하지 말고, 어떤 파일들이 변경되는지 먼저 정리해서 보여준다.
- 큰 작업은 Phase 단위로 나눠서 단계적으로 진행한다.

### 2. 확인하면서 진행 (Interview & Check)

- 모호한 요청이 들어오면 **추정으로 진행하지 말고 질문**한다.
- 각 단계 완료 후 결과를 요약해서 보고하고, 다음 단계로 넘어가기 전에 사용자 확인을 받는다.
- 단, "바로 반영해줘", "계속 진행하자" 같은 명확한 지시에는 즉시 실행한다.

### 3. 항상 테스트 → 커밋

- **커밋 전에 반드시 `pytest tests/ -v` 전체 테스트를 실행**한다.
- 테스트 실패 시 수정 후 재실행하여 전체 통과를 확인한 뒤 커밋한다.
- 새 기능 추가 시 해당 테스트도 함께 작성한다.

### 4. Git 워크플로우

- 작업 브랜치에서 개발 → PR 생성 → **squash merge**로 main에 반영.
- 커밋 메시지는 conventional commits 스타일: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`.
- 푸시 실패 시 rebase 후 재시도. 네트워크 오류는 최대 4회 지수 백오프 재시도.

## 기술 스택

- **언어**: Python 3.10+
- **LLM**: Anthropic Claude API (`claude-sonnet-4-6`), `AsyncAnthropic`
- **테스트**: pytest (212+ tests), API 키 없이 전체 로직 검증
- **프론트엔드**: Streamlit
- **의존성**: requirements.txt 참조

## 프로젝트 구조

```
src/           # 소스 코드 (main.py가 CLI 엔트리포인트)
agents/        # 페르소나 명세서 (*.md) — 프롬프트 튜닝은 여기서
tests/         # pytest 테스트 스위트
meetings/      # 회의록 저장 디렉토리
MANIFESTO.md   # 핵심 가치와 설계 원칙
WHYTREE.md     # Why Tree 분석
PREMORTEM.md   # 사전 부검
glossary.md    # 용어집
```

## 핵심 규칙

- 에이전트 페르소나 수정은 `agents/*.md` 파일 편집으로 한다 (코드 변경 아님).
- 내부 코드 키(`"mentor"`, `"practitioner"`, `"redteam"`, `"clerk"`)는 변경하지 않는다.
- 사용자 표시용 이름은 `src/personas.py`의 `AGENT_CONFIG`에서 관리한다.
- 모든 수치에는 출처를 명시한다 (MANIFESTO 핵심 가치 1번).

## 테스트 실행

```bash
pytest tests/ -v              # 전체 테스트
python src/demo_mock.py       # API 키 없이 Mock 데모
python src/main.py --demo     # 실제 API 데모
```

## 의사소통 언어

- 한국어를 기본으로 사용한다.
- 커밋 메시지와 PR 제목은 한국어 또는 영어 모두 가능.
