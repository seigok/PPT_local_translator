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
    glossary_path: Path | None = None


def _iter_shapes_recursive(shapes) -> Iterable:
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes_recursive(shape.shapes)


def _estimate_font_size_pt(shape, text: str, min_pt: int = 8, max_pt: int = 28) -> int:
    if not text.strip():
        return min_pt
    width_pt = max(1, shape.width.pt)
    height_pt = max(1, shape.height.pt)
    char_count = max(1, len(text.replace("\n", "")))
    line_count = max(1, text.count("\n") + 1)

    est_by_width = width_pt / (0.58 * (char_count / line_count + 2))
    est_by_height = height_pt / (1.5 * line_count)
    est = int(max(min_pt, min(max_pt, min(est_by_width, est_by_height))))
    return est


def _translate_paragraph_with_style_awareness(paragraph, translator: OllamaTranslator) -> str:
    runs = list(paragraph.runs)
    original = "".join(run.text for run in runs) or paragraph.text
    if not original.strip():
        return original

    # Full-context translation.
    short_bullet = paragraph.level > 0 and len(original.strip()) <= 24
    full_translated = translator.translate_en_to_ja(original, short_bullet=short_bullet)

    # If styled runs are present, also do run-level translation to preserve style ranges.
    has_multi_style = len(runs) > 1 and len({(r.font.bold, r.font.italic, r.font.underline, getattr(r.font.color, "rgb", None)) for r in runs}) > 1
    if has_multi_style:
        for run in runs:
            run.text = translator.translate_en_to_ja(run.text, short_bullet=short_bullet)
        return "".join(r.text for r in runs)

    # No meaningful style boundaries: keep full-context result.
    if runs:
        runs[0].text = full_translated
        for run in runs[1:]:
            run.text = ""
    else:
        paragraph.text = full_translated
    return full_translated


def _apply_font_policy(paragraph, shape, translated_text: str) -> None:
    runs = list(paragraph.runs)
    if not runs:
        return

    orig_sizes = []
    for run in runs:
        pt = run.font.size.pt if run.font.size else None
        if pt is not None:
            orig_sizes.append(float(pt))

    max_orig = max(orig_sizes) if orig_sizes else 18.0
    target_max = _estimate_font_size_pt(shape, translated_text, min_pt=8, max_pt=int(max(10, max_orig)))
    scale = min(1.0, target_max / max_orig) if max_orig > 0 else 1.0

    for run in runs:
        run.font.name = "Meiryo"
        base = run.font.size.pt if run.font.size else max_orig
        run.font.size = Pt(max(8, round(base * scale, 1)))


def _translate_text_frame(shape, translator: OllamaTranslator) -> None:
    tf = shape.text_frame
    for paragraph in tf.paragraphs:
        translated_text = _translate_paragraph_with_style_awareness(paragraph, translator)
        _apply_font_policy(paragraph, shape, translated_text)


def _translate_table(shape, translator: OllamaTranslator) -> None:
    table = shape.table
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                translated_text = _translate_paragraph_with_style_awareness(paragraph, translator)
                for run in paragraph.runs:
                    run.font.name = "Meiryo"
                    if run.font.size:
                        run.font.size = Pt(max(8, run.font.size.pt))
                if not paragraph.runs:
                    paragraph.text = translated_text


def translate_ppt(input_path: Path, config: TranslateConfig) -> Path:
    prs = Presentation(str(input_path))
    translator = OllamaTranslator(
        model=config.model,
        base_url=config.base_url,
        glossary_path=config.glossary_path,
    )

    for slide in prs.slides:
        for shape in _iter_shapes_recursive(slide.shapes):
            if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                _translate_text_frame(shape, translator)
            if getattr(shape, "has_table", False) and shape.has_table:
                _translate_table(shape, translator)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = config.output_dir / f"{input_path.stem}_ja.pptx"
    prs.save(str(out_path))
    return out_path
