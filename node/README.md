

```
npm install --dev
```

```
# 通常のユニットテスト
npm run test
```

```
# ミューテーションテスト
npm run stryker  
# キャッシュを残すことができる。
NODE_OPTIONS=--experimental-vm-modules npx stryker run --cleanTempDir false
```


レポートが作成される
node/reports/mutation/mutation.html

