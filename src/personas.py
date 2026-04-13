"""Load persona markdown files and build system prompts for each agent.

Stage 1 (text-based MVP) — persona specs live in /agents/*.md so that
prompt tuning is a file edit, not a code change. This is critical for
Premortem 1-3 (에이전트 역할 뒤죽박죽) countermeasure.
"""
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

AGENT_CONFIG = {
    "practitioner": {
        "name": "실무형",
        "label": "A",
        "file": "practitioner.md",
        "emoji": "📊",
    },
    "redteam": {
        "name": "레드팀",
        "label": "B",
        "file": "redteam.md",
        "emoji": "🔴",
    },
    "mentor": {
        "name": "멘토",
        "label": "C",
        "file": "mentor.md",
        "emoji": "🧭",
    },
    "clerk": {
        "name": "서기",
        "label": "D",
        "file": "clerk.md",
        "emoji": "📝",
    },
}


def load_persona_spec(agent_key: str) -> str:
    """Read the raw markdown persona specification."""
    cfg = AGENT_CONFIG[agent_key]
    return (AGENTS_DIR / cfg["file"]).read_text(encoding="utf-8")


def build_system_prompt(agent_key: str) -> str:
    """Wrap the persona spec into a system prompt for the LLM."""
    spec = load_persona_spec(agent_key)
    return f"""당신은 "말하는 비서실(TalkFile)"의 회의 참석자입니다.
아래 페르소나 명세서를 **엄격히** 따라 응답하세요.

규칙:
- 반드시 한국어로 응답
- 페르소나 명세서의 Must-Do / Must-Not 규칙을 모두 준수
- 최대 2문장 (페르소나 명세서가 더 길게 허용하는 경우 예외 — 예: 서기의 회의록)
- 캐릭터를 절대 깨지 마세요 (시스템·메타정보·다른 에이전트 지칭 금지)
- 다른 참석자의 발언이 먼저 나왔다면 참고하되, 동일 내용을 반복하지 마세요

=== 페르소나 명세서 ===
{spec}
=== 명세서 끝 ===

이제 회의에서 당신이 발언할 차례입니다. 페르소나에 충실히 응답하세요.
"""
