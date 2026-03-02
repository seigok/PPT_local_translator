from ppt_local_translator.ollama_client import OllamaTranslator


def test_ollama_fallback_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("down")

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", boom)
    tr = OllamaTranslator("translategemma:4b")
    text = "Hello Cloud"
    assert tr.translate_en_to_ja(text) == text


def test_strip_markdown_and_extra_newlines(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "**重要**\n\n改善する"}

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", lambda *args, **kwargs: DummyResp())
    tr = OllamaTranslator("translategemma:4b")
    out = tr.translate_en_to_ja("Improve now")
    assert "**" not in out
    assert "\n" not in out


def test_preserve_existing_line_count(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "一行目\n二行目\n三行目"}

    import ppt_local_translator.ollama_client as oc

    monkeypatch.setattr(oc.requests, "post", lambda *args, **kwargs: DummyResp())
    tr = OllamaTranslator("translategemma:4b")
    out = tr.translate_en_to_ja("Line1\nLine2")
    assert out.count("\n") == 1
