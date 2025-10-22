## インストール

```
pipenv install --dev
```

## 単体テストの実行方法

```
pipenv run test test
```

## ミューテーションテスト実行方法

```
# 仮想環境に入る
pipenv shell

# カバレッジに表示
pytest --cov=src --cov-report=json:coverage.json

# セッションを削除
rm -f cr.sqlite

# セッションの初期化 テストコードやテスト対象コードを修正した場合は必要
cosmic-ray init cosmic-ray.toml cr.sqlite

# フィルターを実施
python tool/filter_by_coverage.py cr.sqlite coverage.json

# ベースラインの作成(unitテストが全部合格するのが前提)
cosmic-ray --verbosity=INFO baseline cosmic-ray.toml

# ミューテーションの作成(長時間)
cosmic-ray exec cosmic-ray.toml cr.sqlite

# 結果出力
cr-report cr.sqlite
# レポートをHTMLに
cr-html cr.sqlite > report.html
```

ミューテーション作成時にテスト対象のコードを実際に書き換えてテストをしているので、バージョン管理に保存してから実行したほうが無難。

## 概念
https://cosmic-ray.readthedocs.io/en/latest/concepts.html

### Operator
Cosmic Ray中のOperator は 特定のミューテーションを表すクラスです。

たとえば[cosmic_ray.operators.break_continue](https://github.com/sixty-north/cosmic-ray/blob/master/src/cosmic_ray/operators/break_continue.py)は`break`を`continue`に置き換える操作をするクラスです。

プラグインは[cosmic_ray.operators.operator.Operator](https://github.com/sixty-north/cosmic-ray/blob/master/src/cosmic_ray/operators/operator.py#L9)のサブクラスとして独自のOperatorを実装できます。

### Distributors

Distributorsはテストが実行されるコンテキストを表します。主な例としては以下の２つです。

 - [cosmic_ray.distribution.local.LocalDistributor](https://github.com/sixty-north/cosmic-ray/blob/master/src/cosmic_ray/distribution/local.py#L22): ローカルマシン上でテストを実行
 - [cosmic_ray.distribution.http.HttpDistributor](https://github.com/sixty-north/cosmic-ray/blob/master/src/cosmic_ray/distribution/http.py#L34): HTTP経由でリモートワーカーを利用して並列でテストを実行


### Configurations

configurationは[TOML](https://toml.io/en/)で記載された設定ファイルです。
Cosmic Rayの設定内容については公式の[Creating a configuration](https://cosmic-ray.readthedocs.io/en/latest/tutorials/intro/index.html#creating-a-configuration)を参照してください。

### Sessions

Cosmic Ray には、ミューテーションテストの実行全体を包含する セッション の概念があります。
セッションとは、ある実行のために必要な作業を記録するSqliteのデータベースです。実際のテストを行うワーカーから結果が得られると、このデータベースはその結果で更新されます。このようなデータベースを持つことで、Cosmic Ray は セッションの途中で安全に停止し、再開が可能になります。セッションはどの作業がすでに完了しているかを把握しているため、中断したところから続行できます。
セッションはまた、事後の任意の分析やレポート生成を可能にします。

### テストスイート

ミューテントを殺すために、Cosmic Ray はテストケースを使用します。ただし、より多くのテストケースが失敗しても、ミューテントが「より死んだ」と見なされるわけではないです。1 つのテストケースが失敗すればミューテントを殺すのに十分であるため、失敗したテストケースが見つかり次第終了するようにテストランナーを設定したほうがよいでしょう。。

pytest と nose では、これは -x オプションで実現できます。

また、テストコードについて設定ファイルの`excluded-modules`を使用してのぞいておいたほうがいいでしょう。


