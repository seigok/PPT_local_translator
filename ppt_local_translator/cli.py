from __future__ import annotations

import argparse
from pathlib import Path

from .translator import TranslateConfig, translate_ppt


MODELS = ["translategemma:4b", "translategemma:12b"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="PPT_local_translator")
    p.add_argument("--input", required=True, type=Path, help="input .pptx")
    p.add_argument("--output-dir", required=True, type=Path, help="destination folder")
    p.add_argument("--model", required=True, choices=MODELS)
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--glossary", type=Path, default=Path("./glossary.json"), help="glossary json path")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.input.suffix.lower() != ".pptx":
        raise SystemExit("input must be .pptx")
    out = translate_ppt(
        input_path=args.input,
        config=TranslateConfig(
            model=args.model,
            output_dir=args.output_dir,
            base_url=args.ollama_url,
            glossary_path=args.glossary,
        ),
    )
    print(f"Translated file generated: {out}")


if __name__ == "__main__":
    main()
