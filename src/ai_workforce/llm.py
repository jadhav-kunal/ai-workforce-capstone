import json
from abc import ABC, abstractmethod
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str) -> str:
        raise NotImplementedError


class DemoProvider(LLMProvider):
    """Offline provider used for demos, CI, and reproducible evaluation."""

    def complete(self, system: str, prompt: str) -> str:
        del system
        words = [word.strip(".,:;!?()[]").lower() for word in prompt.split()]
        keywords = []
        for word in words:
            if len(word) > 5 and word not in keywords:
                keywords.append(word)
        focus = ", ".join(keywords[:5]) or "the stated objective"
        return (
            f"Evidence was synthesized around {focus}. The recommended response prioritizes "
            "a measurable outcome, explicit ownership, and a human checkpoint before "
            "external action."
        )


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, system: str, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected LLM response") from exc


def create_provider(provider: str, api_key: str, model: str, base_url: str) -> LLMProvider:
    if provider == "demo":
        return DemoProvider()
    if provider == "openai":
        return OpenAICompatibleProvider(api_key, model, base_url)
    raise ValueError(f"Unsupported provider: {provider}")


def extract_terms(text: str) -> list[str]:
    stop_words = {
        "about",
        "after",
        "before",
        "could",
        "create",
        "should",
        "their",
        "there",
        "these",
        "with",
    }
    terms: list[str] = []
    for raw in text.lower().split():
        word = "".join(character for character in raw if character.isalnum())
        if len(word) >= 4 and word not in stop_words and word not in terms:
            terms.append(word)
    return terms[:8]


def ensure_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)
