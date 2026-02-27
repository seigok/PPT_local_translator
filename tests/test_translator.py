from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from ppt_local_translator import translator as t


class DummyTranslator:
    def __init__(self, *args, **kwargs):
        pass

    def translate_en_to_ja(self, text: str, *, short_bullet: bool = False) -> str:
        return f"JA:{text}"


def test_translate_basic_shape(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(t, "OllamaTranslator", DummyTranslator)

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2))
    p = box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Cloud Native Architecture"
    run.font.bold = True

    in_path = tmp_path / "in.pptx"
    prs.save(in_path)

    out = t.translate_ppt(in_path, t.TranslateConfig(model="translategemma:4b", output_dir=tmp_path))
    out_prs = Presentation(out)
    out_shape = out_prs.slides[0].shapes[0]
    out_text = out_shape.text_frame.paragraphs[0].text

    assert out.exists()
    assert "JA:" in out_text
    assert out_shape.text_frame.paragraphs[0].runs[0].font.name == "Meiryo"


def test_preserve_hyperlink_and_bullet(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(t, "OllamaTranslator", DummyTranslator)

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2))
    p = box.text_frame.paragraphs[0]
    p.level = 1
    run = p.add_run()
    run.text = "Developer Portal"
    run.hyperlink.address = "https://example.com"

    in_path = tmp_path / "link.pptx"
    prs.save(in_path)
    out = t.translate_ppt(in_path, t.TranslateConfig(model="translategemma:4b", output_dir=tmp_path))

    out_prs = Presentation(out)
    p2 = out_prs.slides[0].shapes[0].text_frame.paragraphs[0]
    assert p2.level == 1
    assert p2.runs[0].hyperlink.address == "https://example.com"


def test_estimate_font_size_pt_range():
    class S:
        class D:
            def __init__(self, pt):
                self.pt = pt

        width = D(300)
        height = D(120)

    size = t._estimate_font_size_pt(S(), "short text")
    assert 8 <= size <= 28


def test_style_range_translation_when_multi_run(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(t, "OllamaTranslator", DummyTranslator)

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(7), Inches(2))
    p = box.text_frame.paragraphs[0]
    r1 = p.add_run()
    r1.text = "Private Beta"
    r1.font.bold = True
    r2 = p.add_run()
    r2.text = " starts now"
    r2.font.bold = False

    in_path = tmp_path / "style.pptx"
    prs.save(in_path)

    out = t.translate_ppt(in_path, t.TranslateConfig(model="translategemma:4b", output_dir=tmp_path))
    out_prs = Presentation(out)
    p2 = out_prs.slides[0].shapes[0].text_frame.paragraphs[0]

    assert p2.runs[0].text.startswith("JA:")
    assert p2.runs[1].text.startswith("JA:")
    assert p2.runs[0].font.bold is True
    assert p2.runs[1].font.bold is False
