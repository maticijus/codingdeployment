"""
Writer Agent — generates the essay prep brief via LLM.

Takes curated context blocks from the Curator and produces a structured
markdown brief following the Threeglau style guide.
"""
from src.llm.deepseek import generate
from src.editorial.prompts import build_system_prompt, build_user_prompt


async def write_brief(
    topic: str,
    context_blocks: list[str],
    model: str | None = None,
) -> str:
    """
    Generate a full essay prep brief from curated context.
    Returns the raw markdown string.
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(topic, context_blocks)
    return await generate(system_prompt, user_prompt, model)
