from __future__ import annotations

import re
from pathlib import Path

import requests


_WORD_BOUNDARY = r"[A-Za-z0-9_]"
_GLOSSARY_TOKEN_FMT = "⟪GLS_{:04d}⟫"


class OllamaTranslator:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        glossary_path: Path | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.glossary_path = glossary_path or Path("config/local_glossary")

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

    def _load_glossary_terms(self) -> list[str]:
        path = self.glossary_path
        if not path.exists():
            return []
        terms: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            terms.append(s)
        # deterministic: dedupe while preserving order, then longest-first
        seen: set[str] = set()
        ordered = [t for t in terms if not (t in seen or seen.add(t))]
        ordered.sort(key=lambda x: (-len(x), x))
        return ordered

    def _mask_glossary_terms(self, text: str):
        terms = self._load_glossary_terms()
        if not terms:
            return text, []

        masked = text
        tokens: list[str] = []

        for term in terms:
            pattern = re.compile(
                rf"(?<!{_WORD_BOUNDARY})({re.escape(term)})(?!{_WORD_BOUNDARY})"
            )

            def repl(_m):
                token = _GLOSSARY_TOKEN_FMT.format(len(tokens))
                tokens.append(term)
                return token

            masked = pattern.sub(repl, masked)

        return masked, tokens

    def _unmask_glossary_terms(self, text: str, tokens: list[str]) -> str:
        out = text
        missing: list[str] = []

        for i, term in enumerate(tokens):
            token = _GLOSSARY_TOKEN_FMT.format(i)
            if token not in out:
                missing.append(token)
            out = out.replace(token, term)

        if missing:
            raise ValueError(
                "Glossary placeholder missing after translation: " + ", ".join(missing)
            )
        return out

    def _mask_urls(self, text: str):
        patterns = [
            r"<https?://[^>]+>",
            r"https?://[^\s)\]}>]+",
        ]
        combined = re.compile("|".join(f"({p})" for p in patterns))
        tokens = []

        def repl(m):
            token = f"<<<URLTOKEN_{len(tokens)}>>>"
            tokens.append(m.group(0))
            return token

        masked = combined.sub(repl, text)
        return masked, tokens

    def _unmask_urls(self, text: str, tokens):
        out = text
        for i, v in enumerate(tokens):
            out = out.replace(f"<<<URLTOKEN_{i}>>>", v)

            tolerant = [
                re.compile(rf"URL\s*TOKEN\s*_?\s*{i}", re.IGNORECASE),
                re.compile(rf"URL\s*トークン\s*{i}"),
                re.compile(rf"ＵＲＬ\s*トークン\s*{i}"),
                re.compile(rf"URLトークン\s*{i}"),
            ]
            for pat in tolerant:
                out = pat.sub(v, out)
        return out

    def _sanitize_translation(self, source_text: str, translated: str) -> str:
        out = translated.replace("```", "").replace("**", "").strip("\n")

        if "\n" not in source_text:
            out = out.replace("\n", " ")

        src_lines = source_text.count("\n") + 1
        parts = out.splitlines()
        if len(parts) > src_lines:
            head = parts[: src_lines - 1]
            tail = " ".join(p.strip() for p in parts[src_lines - 1 :] if p.strip())
            out = "\n".join(head + [tail]) if head else tail

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

        masked_core, url_tokens = self._mask_urls(core)
        masked_core, glossary_tokens = self._mask_glossary_terms(masked_core)

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": self._build_prompt(masked_core, short_bullet=short_bullet),
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
            translated = self._unmask_urls(translated, url_tokens)
            translated = self._unmask_glossary_terms(translated, glossary_tokens)
            return f"{leading}{translated}{trailing}" if translated else text
        except ValueError:
            raise
        except Exception:
            return text
