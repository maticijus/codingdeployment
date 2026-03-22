"""Base debater agent with shared LLM call logic via Bytedance R1."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class AgentResponse:
    """Structured response from a debater agent."""

    statement: str
    position: str  # bullish, bearish, neutral, hold
    confidence: float  # 0.0 to 1.0
    reasoning_tags: list[str] = field(default_factory=list)


class DebaterAgent:
    """Base class for investor debater agents.

    Uses Bytedance R1 model via OpenAI-compatible API endpoint.
    """

    name: str = "base"
    personality_prompt: str = ""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        model: str = "ep-20250611114928-bp7sf",
    ):
        self.client = OpenAI(
            api_key=api_key or "PLACEHOLDER_KEY",
            base_url=base_url,
        )
        self.model = model
        self.conversation_history: list[dict] = []

    def _build_system_prompt(self, market_context: str | None = None) -> str:
        """Build the full system prompt with personality and optional market context."""
        parts = [self.personality_prompt]
        if market_context:
            parts.append(
                f"\n\n--- CURRENT MARKET SIGNALS ---\n{market_context}\n"
                "Use these signals to inform your analysis. Reference specific data points."
            )
        parts.append(
            "\n\n--- RESPONSE FORMAT ---\n"
            "You must respond with valid JSON in this exact format:\n"
            "{\n"
            '  "statement": "Your detailed analysis and argument (2-4 paragraphs)",\n'
            '  "position": "bullish|bearish|neutral|hold",\n'
            '  "confidence": 0.0 to 1.0,\n'
            '  "reasoning_tags": ["tag1", "tag2"]\n'
            "}\n"
            "Do NOT include any text outside the JSON object."
        )
        return "\n".join(parts)

    def respond(
        self,
        topic: str,
        debate_history: list[dict] | None = None,
        market_context: str | None = None,
    ) -> AgentResponse:
        """Generate a response to the current debate state.

        Args:
            topic: The debate topic or investment thesis.
            debate_history: Previous rounds of debate statements.
            market_context: Formatted market signal data.

        Returns:
            AgentResponse with the agent's position and reasoning.
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt(market_context)}
        ]

        # Add debate history as conversation context
        if debate_history:
            for entry in debate_history:
                role = "assistant" if entry["agent"] == self.name else "user"
                prefix = f"[{entry['agent'].upper()}]: " if role == "user" else ""
                messages.append({"role": role, "content": f"{prefix}{entry['statement']}"})

        # Current prompt
        if not debate_history:
            messages.append({"role": "user", "content": f"Investment thesis to debate: {topic}"})
        else:
            messages.append({
                "role": "user",
                "content": (
                    "Based on the discussion so far, provide your updated analysis. "
                    "Consider the other debaters' points. If you agree with the emerging "
                    "consensus, state so clearly. If you disagree, explain why with evidence."
                ),
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        raw = response.choices[0].message.content.strip()
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> AgentResponse:
        """Parse the LLM JSON response into an AgentResponse."""
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)

        try:
            data = json.loads(raw)
            return AgentResponse(
                statement=data.get("statement", raw),
                position=data.get("position", "neutral"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning_tags=data.get("reasoning_tags", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback: treat raw text as statement
            return AgentResponse(
                statement=raw,
                position="neutral",
                confidence=0.5,
                reasoning_tags=["parse_fallback"],
            )
