from __future__ import annotations

import requests


class OllamaTranslator:
    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def translate_en_to_ja(self, text: str) -> str:
        if not text or not text.strip():
            return text
        prompt = (
            "Translate the following English text into natural Japanese. "
            "Keep technical terms and product names in English. "
            "Avoid literal translation; prefer context-aware short phrasing. "
            "Return ONLY translated text with original line breaks preserved when possible.\n\n"
            f"TEXT:\n{text}"
        )
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip() or text
        except Exception:
            return text
