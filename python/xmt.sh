#/bin/sh
pytest --cov=src --cov-report=json:coverage.json

# セッションを削除
rm -f cr.sqlite

# セッションの初期化 テストコードやテスト対象コードを修正した場合は必要
cosmic-ray init cosmic-ray.toml cr.sqlite

# フィルターを実施
python tool/filter_by_coverage.py  --verbosity=INFO cr.sqlite coverage.json

# ベースラインの作成(unitテストが全部合格するのが前提)
cosmic-ray --verbosity=INFO baseline cosmic-ray.toml

# ミューテーションの作成(長時間)
cosmic-ray exec cosmic-ray.toml cr.sqlite

# 結果出力
cr-report cr.sqlite
# レポートをHTMLに
cr-html cr.sqlite > report.html
