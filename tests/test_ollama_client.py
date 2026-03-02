from pathlib import Path

from ppt_local_translator.ollama_client import OllamaTranslator


def test_ollama_fallback_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("down")

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", boom)
    tr = OllamaTranslator("translategemma:4b")
    text = "Hello Cloud"
    assert tr.translate_en_to_ja(text) == text


def test_preserve_leading_whitespace_on_fallback(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("down")

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", boom)
    tr = OllamaTranslator("translategemma:4b")
    text = "\t  Infrastructure"
    assert tr.translate_en_to_ja(text) == text


def test_load_glossary_file(tmp_path: Path):
    g = tmp_path / "glossary.json"
    g.write_text('{"do_not_translate":["Kubernetes"]}', encoding="utf-8")
    tr = OllamaTranslator("translategemma:4b", glossary_path=g)
    assert "Kubernetes" in tr.glossary


def test_strip_leading_hallucinated_bullet_block(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": "- Alpha\n- Beta\n- Gamma\n本文です"
            }

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", lambda *args, **kwargs: DummyResp())
    tr = OllamaTranslator("translategemma:4b")
    out = tr.translate_en_to_ja("Improve cloud platform")
    assert out == "本文です"


def test_keep_bullets_when_source_has_bullets(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": "- 項目A\n- 項目B"
            }

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", lambda *args, **kwargs: DummyResp())
    tr = OllamaTranslator("translategemma:4b")
    out = tr.translate_en_to_ja("- Item A\n- Item B")
    assert out == "- 項目A\n- 項目B"
