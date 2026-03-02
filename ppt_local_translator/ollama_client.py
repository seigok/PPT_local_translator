from __future__ import annotations

import json
import re
from pathlib import Path

import requests


DEFAULT_GLOSSARY = ["Infrastructure", "Private Beta", "Public Beta"]


class OllamaTranslator:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        glossary_path: Path | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.glossary_path = glossary_path
        self.glossary = self._load_glossary(glossary_path)

    def _load_glossary(self, glossary_path: Path | None) -> list[str]:
        terms = list(DEFAULT_GLOSSARY)
        if not glossary_path:
            return terms
        try:
            data = json.loads(Path(glossary_path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("do_not_translate"), list):
                for term in data["do_not_translate"]:
                    if isinstance(term, str) and term.strip() and term not in terms:
                        terms.append(term)
        except Exception:
            pass
        return terms

    def _build_prompt(self, text: str, *, short_bullet: bool = False) -> str:
        glossary_block = ", ".join(self.glossary)
        short_sentence_rule = (
            "For very short bullet items or very short standalone lines, do not append Japanese period '。'."
            if short_bullet
            else ""
        )
        return (
            "Translate the following English text into natural Japanese for technical slides. "
            "Keep technical terms and product names in English, strictly preserving the glossary terms. "
            "Avoid literal translation; prefer concise, context-aware phrasing Japanese users prefer. "
            "Preserve leading indentation spaces/tabs and keep meaningful line breaks at semantic boundaries. "
            f"{short_sentence_rule}\n\n"
            "Do-not-translate glossary:\n"
            f"{glossary_block}\n\n"
            "Return ONLY translated text.\n\n"
            f"TEXT:\n{text}"
        )


    def _sanitize_translation(self, source_text: str, translated: str) -> str:
        """Remove known hallucinated glossary bullets and prompt-echo artifacts."""
        out = translated.replace("```", "").strip("\n")

        # If source has no explicit '-' bullets, drop standalone injected bullet lines.
        source_has_dash = "-" in source_text

        artifact_lines = {
            "- インフラ",
            "- プライベートベータ",
            "- パブリックベータ",
            "-",
        }

        cleaned_lines = []
        for line in out.splitlines():
            normalized = line.strip()
            if not source_has_dash and normalized in artifact_lines:
                continue
            # Also remove optional leading-space variants like " - プライベートベータ"
            if not source_has_dash and normalized.startswith("-") and normalized[1:].strip() in {"インフラ", "プライベートベータ", "パブリックベータ"}:
                continue
            cleaned_lines.append(line)

        # collapse excessive empty lines
        collapsed = []
        prev_empty = False
        for line in cleaned_lines:
            empty = (line.strip() == "")
            if empty and prev_empty:
                continue
            collapsed.append(line)
            prev_empty = empty

        return "\n".join(collapsed).strip("\n")

    def translate_en_to_ja(self, text: str, *, short_bullet: bool = False) -> str:
        if not text:
            return text

        # Preserve leading/trailing whitespace exactly.
        lead_match = re.match(r"^[\t ]+", text)
        trail_match = re.search(r"[\t ]+$", text)
        leading = lead_match.group(0) if lead_match else ""
        trailing = trail_match.group(0) if trail_match else ""
        core = text[len(leading) : len(text) - len(trailing) if trailing else len(text)]

        if not core.strip():
            return text

        prompt = self._build_prompt(core, short_bullet=short_bullet)
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
            translated = data.get("response", "")
            if not translated:
                return text
            translated = self._sanitize_translation(core, translated)
            if not translated:
                return text
            return f"{leading}{translated}{trailing}"
        except Exception:
            return text
