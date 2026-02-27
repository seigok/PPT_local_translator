# IMPLEMENTATION LOG

- プロジェクト雛形作成（CLI / translator / Ollama client）
- `.gitignore` に source/dest/models と `*.pptx` を追加
- Shape再帰走査（GroupShape対応）と table テキスト翻訳を実装
- 翻訳ポリシー（文脈重視・短文・技術用語維持）をプロンプト化
- メイリオ固定、フォントサイズpt再計算ヒューリスティックを実装
- 単体テスト（translator / cli）を作成
- ネット由来サンプルPPT取得スクリプトを追加
- 実行: `pytest -q` => 5 passed
- 実行: `bash tests/download_sample_ppt.sh` => `source/sample_from_web.pptx` (Microsoft PowerPoint 2007+)
