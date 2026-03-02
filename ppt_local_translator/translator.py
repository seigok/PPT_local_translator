from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Pt

from .ollama_client import OllamaTranslator


@dataclass
class TranslateConfig:
    model: str
    output_dir: Path
    base_url: str = "http://localhost:11434"


def _iter_shapes_recursive(shapes) -> Iterable:
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes_recursive(shape.shapes)


def _is_probably_japanese(text: str) -> bool:
    if not text.strip():
        return True
    jp = sum(1 for ch in text if ("\u3040" <= ch <= "\u30ff") or ("\u4e00" <= ch <= "\u9fff"))
    return jp / max(1, len(text)) > 0.25


def _set_font_preserve_size(run) -> None:
    # Keep original explicit run size as-is. If size is inherited(None), do not override.
    original_size = run.font.size
    run.font.name = "Meiryo"
    if original_size is not None:
        run.font.size = original_size


def _is_bullet_like(paragraph) -> bool:
    text = (paragraph.text or "").strip()
    return paragraph.level > 0 or text.startswith(("-", "•", "・"))


def _shape_is_transparent_background(shape) -> bool:
    try:
        fill = getattr(shape, "fill", None)
        if fill is None:
            return True
        return fill.type is None
    except Exception:
        return False


def _estimate_line_width_pt(text: str, font_pt: float) -> float:
    # rough heuristic for Japanese: full-width-ish average
    return max(40.0, len(text.strip()) * font_pt * 1.05)


def _adjust_textbox_width_for_short_lines(shape, paragraphs) -> None:
    non_empty = [p for p in paragraphs if (p.text or "").strip()]
    if not non_empty:
        return

    # apply when all non-empty lines are short bullet-like lines (<=30 chars)
    if not all(_is_bullet_like(p) and len((p.text or "").strip()) <= 30 for p in non_empty):
        return

    # if transparent rectangle/shape, always eligible; otherwise still allow for bullets
    _ = _shape_is_transparent_background(shape)

    # use longest line, not first line
    longest = max(non_empty, key=lambda p: len((p.text or "").strip()))
    first_run = longest.runs[0] if longest.runs else None
    font_pt = first_run.font.size.pt if (first_run and first_run.font.size) else 18.0
    target_width = _estimate_line_width_pt(longest.text or "", font_pt)

    if shape.width.pt > target_width:
        shape.width = Pt(target_width)


def _translate_paragraph(paragraph, translator: OllamaTranslator) -> None:
    runs = list(paragraph.runs)
    original = "".join(run.text for run in runs) if runs else (paragraph.text or "")

    # keep explicit blank line as-is (do not collapse)
    if original == "":
        return
    if not original.strip():
        return

    # Repeat-translation guard
    if _is_probably_japanese(original):
        for run in runs:
            _set_font_preserve_size(run)
        return

    short_bullet = _is_bullet_like(paragraph) and len(original.strip()) <= 30

    # Preserve mid-sentence color/style by translating per-run when multiple runs exist.
    if len(runs) > 1:
        for run in runs:
            if not run.text.strip() or _is_probably_japanese(run.text):
                _set_font_preserve_size(run)
                continue
            run.text = translator.translate_en_to_ja(run.text, short_bullet=short_bullet)
            _set_font_preserve_size(run)
        return

    translated = translator.translate_en_to_ja(original, short_bullet=short_bullet)
    if runs:
        runs[0].text = translated
        _set_font_preserve_size(runs[0])
    else:
        paragraph.text = translated


def _translate_text_frame(shape, translator: OllamaTranslator) -> None:
    tf = shape.text_frame
    paragraphs = list(tf.paragraphs)
    for paragraph in paragraphs:
        _translate_paragraph(paragraph, translator)
    _adjust_textbox_width_for_short_lines(shape, paragraphs)


def _translate_table(shape, translator: OllamaTranslator) -> None:
    table = shape.table
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                _translate_paragraph(paragraph, translator)


def _translate_slide_notes(slide, translator: OllamaTranslator) -> None:
    if not slide.has_notes_slide:
        return
    notes_tf = slide.notes_slide.notes_text_frame
    for paragraph in notes_tf.paragraphs:
        _translate_paragraph(paragraph, translator)


def translate_ppt(input_path: Path, config: TranslateConfig) -> Path:
    prs = Presentation(str(input_path))
    translator = OllamaTranslator(model=config.model, base_url=config.base_url)

    for slide in prs.slides:
        for shape in _iter_shapes_recursive(slide.shapes):
            if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                _translate_text_frame(shape, translator)
            if getattr(shape, "has_table", False) and shape.has_table:
                _translate_table(shape, translator)
        _translate_slide_notes(slide, translator)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = config.output_dir / f"{input_path.stem}_ja.pptx"
    prs.save(str(out_path))
    return out_path
