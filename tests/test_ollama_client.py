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


def test_strip_hallucinated_glossary_bullets(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": "- インフラ\n - プライベートベータ\n - パブリックベータ\n-\nクラウド基盤を改善します"
            }

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", lambda *args, **kwargs: DummyResp())
    tr = OllamaTranslator("translategemma:4b")
    out = tr.translate_en_to_ja("Improve cloud platform")
    assert "インフラ" not in out
    assert "プライベートベータ" not in out
    assert "パブリックベータ" not in out
    assert out == "クラウド基盤を改善します"
