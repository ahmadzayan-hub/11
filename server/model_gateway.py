"""Provider-neutral model gateway.

LLMs may phrase and summarize; they never calculate. Every number in a
report comes from deterministic code, and the gateway is only offered the
already-computed facts. With no provider configured (the default, and
always in tests/CI) a deterministic template is used, so the application
is fully functional offline and no test ever needs credentials.

Groq support is configured exclusively through server-side environment
variables (GROQ_API_KEY, GROQ_MODEL). Keys are never logged, stored, or
sent to the browser; provider errors degrade safely to the deterministic
narrator and are reported as such.
"""

import os

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
TIMEOUT_SECONDS = 12


class ModelGateway:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY") or None
        self.model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    def status(self):
        return {
            "provider": "groq" if self.api_key else "deterministic",
            "model": self.model if self.api_key else None,
            "configured": bool(self.api_key),
        }

    def narrate(self, goal, facts):
        """Return {'text', 'source'} where source is 'model' or
        'deterministic'. Facts are short verified statements; the model is
        asked only to phrase them, never to add numbers or claims."""
        if self.api_key:
            text = self._call_groq(goal, facts)
            if text:
                return {"text": text, "source": "model"}
        summary = " ".join(facts[:4])
        return {
            "text": f"Analysis of the goal “{goal}”: {summary}",
            "source": "deterministic",
        }

    def _call_groq(self, goal, facts):
        try:
            import httpx

            response = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "max_tokens": 220,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You write two-sentence executive summaries. "
                                "Use ONLY the verified facts provided. Do not "
                                "add numbers, causes, or claims of your own."
                            ),
                        },
                        {
                            "role": "user",
                            "content": "Goal: " + goal + "\nVerified facts:\n- "
                            + "\n- ".join(facts),
                        },
                    ],
                },
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                return None
            content = response.json()["choices"][0]["message"]["content"]
            return content.strip() if isinstance(content, str) and content.strip() else None
        except Exception:
            # Timeouts, network, schema drift: degrade to deterministic.
            return None
