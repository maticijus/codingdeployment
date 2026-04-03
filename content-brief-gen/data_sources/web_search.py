"""Use Grok (xAI) with x_search tool for real-time web context."""
import httpx
from config import XAI_API_KEY


async def search_current_context(topic: str, domain_hint: str = "") -> str:
    """
    Use Grok's Responses API with x_search to get current news/social context.
    Returns a text summary of what's happening right now re: the topic.
    """
    if not XAI_API_KEY:
        return "[No XAI_API_KEY set — skipping web search enrichment]"

    search_prompt = f"""Find the most recent news, data, and social media discussion about: {topic}

Focus on:
- Any data releases, reports, or forecasts from the last 30 days
- Current market prices or conditions relevant to this topic
- Notable expert commentary or analysis
- Upcoming events or catalysts

{f"Domain context: this is related to {domain_hint}" if domain_hint else ""}

Provide factual, dated information only. No opinions. Include source names."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                "https://api.x.ai/v1/responses",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-3-mini",
                    "tools": [{"type": "web_search"}],
                    "input": search_prompt,
                    "temperature": 0.2,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extract text from output blocks
                output = data.get("output", [])
                text_parts = []
                for block in output:
                    if block.get("type") == "message":
                        for content in block.get("content", []):
                            if content.get("type") == "output_text":
                                text_parts.append(content.get("text", ""))
                    elif block.get("type") == "output_text":
                        text_parts.append(block.get("text", ""))

                return "Current Context (via web search):\n" + "\n".join(text_parts) if text_parts else "[Web search returned no results]"
            else:
                return f"[Grok search failed: HTTP {resp.status_code}]"
        except Exception as e:
            return f"[Grok search error: {e}]"
