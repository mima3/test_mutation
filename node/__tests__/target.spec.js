import { Target, computeOrderTotal } from "../src/target.js"

describe('Target', ()=> {
  test('isAdult', ()=> {
    const obj = new Target();
    console.log(obj.isAdult(20));
    expect(obj.isAdult(20)).toBeTruthy();
    expect(obj.isAdult(21)).toBeTruthy();
    expect(obj.isAdult(19)).not.toBeTruthy();
  });
  test('add', ()=> {
    const obj = new Target();
    console.log(obj.add(1, 2));
    // expect(obj.add(1, 2)).toEqual(3);
  });

});

describe('computeOrderTotal の単体テスト（ステートメントカバレッジ重視）', () => {
  test('空配列は 0 を返す（早期return）', () => {
    expect(computeOrderTotal([])).toBe(0);
  });
  test('配列以外は 0 を返す（早期return）', () => {
    expect(computeOrderTotal(null)).toBe(0);
  });

  test('不正行（欠落・負値・数量0）はスキップされ、すべて無効なら 0', () => {
    const cart = [
      null,                                         // 行欠落
      { price: undefined, qty: 1 },                 // price 欠落
      { price: 100, qty: undefined },               // qty 欠落
      { price: -5, qty: 2 },                        // 価格負
      { price: 10, qty: 0 },                        // 数量0
    ];
    expect(computeOrderTotal(cart)).toBe(0);
  });

  test('通常ケース：送料あり（例示と同じ数値）', () => {
    const cart = [
      { price: 20, qty: 2 },
      { price: 15, qty: 1, weight: 0.4 }, // 重量>0 の経路を通す
    ];
    const opts = { taxRate: 0.1, freeShipThreshold: 100, shipPerKg: 3 };
    // 小計=55 → 税込=60.5、重量=0.4→ceil=1 → 送料=3 → 合計=63.5
    expect(computeOrderTotal(cart, opts)).toBe(63.5);
  });

  test('贅沢品フラグで税率+5%（水曜5%引きも適用）', () => {
    const cart = [{ price: 100, qty: 1, category: 'lux', weight: 1.2 }];
    const opts = { dayOfWeek: 3, taxRate: 0.1, freeShipThreshold: 120, shipPerKg: 2.5 };
    // 例示値：114.25
    expect(computeOrderTotal(cart, opts)).toBe(114.25);
  });

  test('プロモ SAVE10 は曜日割引より強い（大きい方のみ）。副作用カウンタが +1 される', () => {
    const counters = { promoUsed: 0 };
    const cart = [
      { price: 90, qty: 1, weight: 0.5 },
      { price: 30, qty: 1 },
    ];
    const opts = { promoCode: 'SAVE10', counters, freeShipThreshold: 110 };
    // 例示値：118.8、promoUsed は +1
    expect(computeOrderTotal(cart, opts)).toBe(118.8);
    expect(counters.promoUsed).toBe(1);
  });

  test('送料の閾値：税込が閾値未満なら送料あり、ちょうど・超えなら送料無料', () => {
    // 税率0にして税込=小計に合わせる（丸めの影響を回避）
    const base = { taxRate: 0, shipPerKg: 5, freeShipThreshold: 100 };

    // 未満（99.99）→ 送料が発生（重量 0.4 → ceil=1 → 5）
    expect(
      computeOrderTotal(
        [{ price: 99.99, qty: 1, weight: 0.4 }],
        base
      )
    ).toBe(99.99 + 5); // 104.99

    // ちょうど（100）→ 送料無料
    expect(
      computeOrderTotal(
        [{ price: 100, qty: 1, weight: 10 }],
        base
      )
    ).toBe(100);

    // 超え（120）→ 送料無料
    expect(
      computeOrderTotal(
        [{ price: 60, qty: 2, weight: 10 }],
        base
      )
    ).toBe(120);
  });

  test('重量の切り上げ境界を確認（0, 0.01, 0.99, 1.0）', () => {
    const opts = { taxRate: 0, freeShipThreshold: 9999, shipPerKg: 3 }; // 送料無料にならないよう高閾値
    // 0.00 kg → ceil(0)=0 → 送料0
    expect(computeOrderTotal([{ price: 10, qty: 1, weight: 0.0 }], opts)).toBe(10);
    // 0.01 kg → ceil(0.01)=1 → 送料3
    expect(computeOrderTotal([{ price: 10, qty: 1, weight: 0.01 }], opts)).toBe(13);
    // 0.99 kg → ceil(0.99)=1 → 送料3
    expect(computeOrderTotal([{ price: 10, qty: 1, weight: 0.99 }], opts)).toBe(13);
    // 1.00 kg → ceil(1)=1 → 送料3
    expect(computeOrderTotal([{ price: 10, qty: 1, weight: 1.0 }], opts)).toBe(13);
  });

  test('プロモなし・水曜でもない（割引0）の経路を通す（hasLuxury=false側の税率も確認）', () => {
    const cart = [
      { price: 50, qty: 1, category: 'normal', weight: 0 },
      { price: 10, qty: 2 }, // subtotal=70
    ];
    const opts = { taxRate: 0.08, dayOfWeek: 2, freeShipThreshold: 100, shipPerKg: 4 };
    // 割引0、税8% → 税込=75.6、重量=0 → 送料=4*ceil(0)=0 → 合計=75.6
    expect(computeOrderTotal(cart, opts)).toBe(75.6);
  });

  test('行スキップの分岐（weight 未指定・<=0 の経路）とカテゴリ未指定を通す', () => {
    const cart = [
      { price: 10, qty: 1 },            // weight 未指定（0扱い）、category 未指定
      { price: 5, qty: 2, weight: 0 },  // weight 0（加算しない）
    ];
    const opts = { taxRate: 0.1, freeShipThreshold: 9999, shipPerKg: 10 };
    // subtotal=20、tax=10% → 22、重量=0 → 送料0 → 合計22
    expect(computeOrderTotal(cart, opts)).toBe(22);
  });
});