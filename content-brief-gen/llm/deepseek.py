"""DeepSeek R1 / V3 client for brief generation."""
import httpx
from config import DEEPSEEK_API_KEY, DEFAULT_MODEL

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


async def generate_brief(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    """Call DeepSeek to generate the structured brief."""
    model = model or DEFAULT_MODEL

    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    # DeepSeek R1 (reasoner) doesn't accept system messages — merge into user
    if model == "deepseek-reasoner":
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n---\n\n{user_prompt}"}
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 8000,
                "temperature": 0.4,  # Creative but controlled
                "stream": False,
            },
        )

        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek API error: {resp.status_code} — {resp.text[:500]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]
