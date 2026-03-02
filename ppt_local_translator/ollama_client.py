from __future__ import annotations

import re

import requests


class OllamaTranslator:
    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _build_prompt(self, text: str, *, short_bullet: bool = False) -> str:
        short_sentence_rule = (
            "For very short bullet items or very short standalone lines, do not append Japanese period '。'."
            if short_bullet
            else ""
        )
        return (
            "Translate the following English text into natural Japanese for technical slides. "
            "Use plain text only (no markdown symbols like ** or _). "
            "Do not add line breaks that are not present in the source text. "
            "Use 'だ・である' style where natural, and concise noun-ending phrases when appropriate. "
            "Keep leading indentation spaces/tabs exactly as-is. "
            "Keep technical terms in English when needed. "
            f"{short_sentence_rule}\n\n"
            "Return ONLY translated text.\n\n"
            f"TEXT:\n{text}"
        )

    def _sanitize_translation(self, source_text: str, translated: str) -> str:
        out = translated.replace("```", "").replace("**", "").strip("\n")

        # Do not insert new line breaks if source had none.
        if "\n" not in source_text:
            out = out.replace("\n", " ")

        # If source has N lines, cap output lines to N by joining extras.
        src_lines = source_text.count("\n") + 1
        parts = out.splitlines()
        if len(parts) > src_lines:
            head = parts[: src_lines - 1]
            tail = " ".join(p.strip() for p in parts[src_lines - 1 :] if p.strip())
            out = "\n".join(head + [tail]) if head else tail

        # collapse excessive spaces
        out = re.sub(r"[ \t]{2,}", " ", out)
        return out.strip("\n")

    def translate_en_to_ja(self, text: str, *, short_bullet: bool = False) -> str:
        if not text:
            return text

        lead_match = re.match(r"^[\t ]+", text)
        trail_match = re.search(r"[\t ]+$", text)
        leading = lead_match.group(0) if lead_match else ""
        trailing = trail_match.group(0) if trail_match else ""
        core = text[len(leading) : len(text) - len(trailing) if trailing else len(text)]

        if not core.strip():
            return text

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": self._build_prompt(core, short_bullet=short_bullet),
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("response", "")
            if not translated:
                return text
            translated = self._sanitize_translation(core, translated)
            return f"{leading}{translated}{trailing}" if translated else text
        except Exception:
            return text
