/**
 * @typedef {'food'|'lux'|'normal'} ItemCategory
 * @typedef {Object} CartItem
 * @property {number} price                 単価（0以上）。欠落・不正はスキップ。
 * @property {number} qty                   数量（1以上）。欠落・不正はスキップ。
 * @property {ItemCategory} [category]      任意。'lux' を含むと贅沢品扱い（税率+5%）。
 * @property {number} [weight]              1個あたり重量[kg]（0以上、任意）。送料計算に使用。
 */

/**
 * @typedef {Object} Counters
 * @property {number} promoUsed             プロモコード適用回数（副作用で +1）。
 */

/**
 * @typedef {Object} Options
 * @property {number} [taxRate=0.10]               基本税率（0.10 = 10%）。
 * @property {number} [freeShipThreshold=100]      税込金額がこの閾値以上なら送料0円。
 * @property {number} [shipPerKg=2.5]              送料の単価（kgあたり、重量は切り上げ）。
 * @property {string} [promoCode]                  'SAVE10' なら10%引き（曜日割引と重ね不可：大きい方のみ適用）。
 * @property {number} [dayOfWeek]                  曜日（0=日, 1=月, …, 3=水）。水曜は5%引き。
 * @property {Counters} [counters]                 副作用を観測するためのカウンタ。
 */
/**
 * カートから最終支払額（>=0、少数2桁）を計算する。
 *
 * 仕様概要:
 *  - 不正行（price欠落/負、qty欠落/<=0）はスキップ。
 *  - 贅沢品を1つでも含むと税率に +5%。
 *  - 水曜（dayOfWeek===3）は小計の5%引き。
 *  - プロモコード 'SAVE10' は小計の10%引き。曜日割引と**重ね不可**（大きい方を採用）。
 *  - 割引適用後に税計算。丸めは都度 `Math.round(x*100)/100` で小数2桁。
 *  - 税込金額が閾値以上なら送料0円、未満なら `ceil(総重量[kg]) * shipPerKg`。
 *  - 'SAVE10' 適用時に `counters.promoUsed` を +1（副作用）。
 *  - 空配列や有効行がない場合は 0 を返す（早期return）。
 *
 * @param {CartItem[]} cart   カート明細配列。
 * @param {Options} [opts={}] 設定オプション。
 * @returns {number} 最終支払額（>=0、小数2桁に丸め）。
 *
 * @example
 * // 通常商品のみで送料あり
 * computeOrderTotal([{ price: 20, qty: 2 }, { price: 15, qty: 1, weight: 0.4 }], {
 *   taxRate: 0.1, freeShipThreshold: 100, shipPerKg: 3
 * }); // -> 63.5
 *
 * @example
 * // 贅沢品＋水曜割引（5%）、送料あり
 * computeOrderTotal([{ price: 100, qty: 1, category: 'lux', weight: 1.2 }], {
 *   dayOfWeek: 3, taxRate: 0.1, freeShipThreshold: 120, shipPerKg: 2.5
 * }); // -> 114.25
 *
 * @example
 * // プロモSAVE10（水曜より強い）、送料無料・副作用のカウント
 * const counters = { promoUsed: 0 };
 * computeOrderTotal([{ price: 90, qty: 1, weight: 0.5 }, { price: 30, qty: 1 }], {
 *   promoCode: 'SAVE10', counters, freeShipThreshold: 110
 * }); // -> 118.8, counters.promoUsed === 1
 */
export function computeOrderTotal(cart, opts = {}) {
  // 入力ガード：配列でなければ、または空なら 0（早期return）
  if (!Array.isArray(cart) || cart.length === 0) return 0;

  // オプションの正規化（未指定時のデフォルト値）
  const taxRate = typeof opts.taxRate === 'number' ? opts.taxRate : 0.10;                 // 基本税率10%
  const freeShipThreshold = typeof opts.freeShipThreshold === 'number' ? opts.freeShipThreshold : 100;
  const shipPerKg = typeof opts.shipPerKg === 'number' ? opts.shipPerKg : 2.5;

  // 集計用変数
  let subtotal = 0;        // 小計：price * qty の総和
  let totalWeight = 0;     // 総重量：weight * qty の総和
  let hasLuxury = false;   // 贅沢品を含むか

  // ループ：各明細を検査しながら集計
  for (const item of cart) {
    // 欠落・未定義の行はスキップ
    if (!item || item.price == null || item.qty == null) continue;
    // 不正値（負の価格、0以下の数量）はスキップ
    if (item.price < 0 || item.qty <= 0) continue;

    // 行の金額を小計に足す
    const line = item.price * item.qty;
    subtotal += line;

    // 重量があれば総重量に加算（未指定は0扱い）
    const w = item.weight ?? 0;
    if (w > 0) totalWeight += w * item.qty;

    // カテゴリが 'lux' ならフラグを立てる
    if (item.category === 'lux') hasLuxury = true;
  }

  // 有効行がなければ 0（早期return）
  if (subtotal === 0) return 0;

  // 分岐1：贅沢品あり → 税率+5%、なければ基本税率
  const effectiveTax = hasLuxury ? taxRate + 0.05 : taxRate;

  // 分岐2：水曜割引（5%）
  const isMidweek = opts.dayOfWeek === 3;      // 0=日 … 3=水
  let discount = isMidweek ? subtotal * 0.05 : 0;

  // 分岐3：プロモ 'SAVE10'（10%）。曜日割引と重ね不可 → 大きい方のみ採用
  if (opts.promoCode === 'SAVE10') {
    // 副作用：カウンタが渡されていれば +1（テスト観測点）
    if (opts.counters && typeof opts.counters.promoUsed === 'number') {
      opts.counters.promoUsed += 1;
    }
    discount = Math.max(discount, subtotal * 0.10);
  }

  // 割引後に税を適用。小数2桁で丸め
  const taxed = Math.round((subtotal - discount) * (1 + effectiveTax) * 100) / 100;

  // 分岐4：税込みが閾値以上なら送料無料、未満なら 送料=ceil(総重量)*単価
  const shipping =
    taxed >= freeShipThreshold ? 0 : Math.ceil(totalWeight) * shipPerKg;

  // 最終額：負にならないよう 0 で下限、2桁丸め
  const total = Math.max(0, Math.round((taxed + shipping) * 100) / 100);
  return total;
}

export class Target {
  isAdult(age) {
    return age >= 20;
  }
  add(x, y) {
    return x + y;
  }
}
