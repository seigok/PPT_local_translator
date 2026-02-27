# PPT_local_translator

PowerPoint（.pptx）をローカル Ollama モデルで英語→日本語翻訳する CLI ツール。

## 特徴
- 入力: CLI引数で `.pptx`
- 出力: 指定フォルダへ翻訳済み `.pptx`
- GroupShape を含む複雑 Shape の再帰走査
- 翻訳方針: 文脈重視・短文・技術用語は英語維持
- フォントを **メイリオ固定**
- 太字/斜体/色/ハイパーリンク/箇条書きの維持を優先
- フォントサイズを絶対値（pt）で再設定し、枠内に収まるようヒューリスティック調整
- Ollama モデル選択: `translategemma:4b` / `translategemma:12b`

## セットアップ
```bash
cd PPT_local_translator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使い方
```bash
python -m ppt_local_translator.cli \
  --input ./source/input.pptx \
  --output-dir ./dest \
  --model translategemma:4b
```

実行後、`dest/<元ファイル名>_ja.pptx` を生成します。

## 事前条件
- Ollama が起動済みであること
- 使うモデルを pull 済みであること（例: `ollama pull translategemma:4b`）


## Ollama セットアップ（macOS）
```bash
brew install ollama
brew services start ollama
ollama pull translategemma:4b
# 必要なら
# ollama pull translategemma:12b
```

動作確認:
```bash
ollama --version
ollama list
```

## テスト
```bash
pytest -q
```

E2E（実際にOllamaで翻訳）:
```bash
pytest -q -m e2e
```

### ネット由来サンプルPPT調達
```bash
bash tests/download_sample_ppt.sh
```
取得できた場合、`source/sample_from_web.pptx` で手動確認可能です。

## 注意
- モデルや PPT ファイルは git 管理対象外（`.gitignore`）
- SmartArt など python-pptx が直接扱えないオブジェクトは制約あり
