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


def _estimate_font_size_pt(shape, text: str, min_pt: int = 10, max_pt: int = 28) -> int:
    if not text.strip():
        return min_pt
    width_pt = max(1, shape.width.pt)
    height_pt = max(1, shape.height.pt)
    char_count = max(1, len(text.replace("\n", "")))
    line_count = max(1, text.count("\n") + 1)

    est_by_width = width_pt / (0.55 * (char_count / line_count + 2))
    est_by_height = height_pt / (1.4 * line_count)
    est = int(max(min_pt, min(max_pt, min(est_by_width, est_by_height))))
    return est


def _redistribute_text_to_runs(paragraph, translated_text: str) -> None:
    runs = list(paragraph.runs)
    if not runs:
        paragraph.text = translated_text
        return

    total = sum(max(1, len(r.text)) for r in runs)
    idx = 0
    remaining = translated_text
    for i, run in enumerate(runs):
        if i == len(runs) - 1:
            run.text = remaining
            break
        weight = max(1, len(run.text)) / total
        take = int(round(len(translated_text) * weight))
        chunk = translated_text[idx : idx + take]
        run.text = chunk
        idx += len(chunk)
        remaining = translated_text[idx:]


def _translate_text_frame(shape, translator: OllamaTranslator) -> None:
    tf = shape.text_frame
    for paragraph in tf.paragraphs:
        original = "".join(run.text for run in paragraph.runs) or paragraph.text
        if not original.strip():
            continue

        translated = translator.translate_en_to_ja(original)
        _redistribute_text_to_runs(paragraph, translated)

        size_pt = _estimate_font_size_pt(shape, translated)
        for run in paragraph.runs:
            run.font.name = "Meiryo"
            run.font.size = Pt(size_pt)


def _translate_table(shape, translator: OllamaTranslator) -> None:
    table = shape.table
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                original = "".join(run.text for run in paragraph.runs) or paragraph.text
                if not original.strip():
                    continue
                translated = translator.translate_en_to_ja(original)
                _redistribute_text_to_runs(paragraph, translated)
                for run in paragraph.runs:
                    run.font.name = "Meiryo"
                    run.font.size = Pt(14)


def translate_ppt(input_path: Path, config: TranslateConfig) -> Path:
    prs = Presentation(str(input_path))
    translator = OllamaTranslator(model=config.model, base_url=config.base_url)

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
