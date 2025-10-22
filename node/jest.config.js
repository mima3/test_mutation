// ESMなので export default を使う
export default {
  testEnvironment: 'node',
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/src/$1'
  },
  // stryker-tmpのキャッシュをみない
  testPathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
  watchPathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
  // ← ここに extensionsToTreatAsEsm は書かない（削除）
  transform: {} // 変換なし（Babel使わない場合）
};
