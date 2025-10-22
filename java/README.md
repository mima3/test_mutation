## 実行方法


**ビルド結果のクリア**

```bash
mvn clean
```

**単体テストの実行方法**

```bash
mvn test
```

**pitestの実行方法**

ユニットテスト実行後、以下を実行

```bash
mvn org.pitest:pitest-maven:1.21.0:mutationCoverage
```

以下にカバレッジレポートが表示される

java/target/pit-reports/example/index.html