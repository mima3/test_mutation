package example;

import java.util.List;
import java.util.Objects;

/**
 * 注文合計を計算するユーティリティ（ループ／複数分岐／早期return／副作用を含む）。
 * <p>
 * 目的：ミューテーションテストに向いた関数構造を Java で再現します。
 * 金額計算は JS 実装に合わせて double を用い、丸めは都度 {@code Math.round(x * 100) / 100.0}
 * で小数2桁に揃えます（実務では BigDecimal 推奨）。
 *
 * <h3>仕様概要</h3>
 * <ul>
 *   <li>不正行（price 欠落/負、qty 欠落/<=0）はスキップ。</li>
 *   <li>贅沢品（category == LUX）を1つでも含むと税率に +5%。</li>
 *   <li>水曜（dayOfWeek == 3）は小計の 5% 引き。</li>
 *   <li>プロモコード "SAVE10" は小計の 10% 引き。曜日割引と<strong>重ね不可</strong>（大きい方のみ適用）。</li>
 *   <li>割引適用後に税を計算。小数2桁で丸め。</li>
 *   <li>税込金額が閾値以上なら送料 0、未満なら {@code ceil(総重量[kg]) * shipPerKg}。</li>
 *   <li>"SAVE10" 適用時は counters.promoUsed を +1（副作用）。</li>
 *   <li>cart が null/空、または有効行が無い場合は 0 を返す（早期 return）。</li>
 * </ul>
 *
 * <h3>使用例</h3>
 * <pre>{@code
 * List<CartItem> cart = List.of(
 *     new CartItem(20, 2, ItemCategory.NORMAL, null),
 *     new CartItem(15, 1, ItemCategory.NORMAL, 0.4)
 * );
 * Options opt = new Options().setTaxRate(0.1).setFreeShipThreshold(100).setShipPerKg(3);
 * double total = OrderCalculator.computeOrderTotal(cart, opt); // => 63.5
 * }</pre>
 */
public final class OrderCalculator {

  private OrderCalculator() {}

  /** アイテムカテゴリ。 */
  public enum ItemCategory { FOOD, LUX, NORMAL }

  /** カート1行分。欠落値は null 許容。 */
  public static final class CartItem {
    private final Double price;        // 単価（0以上）
    private final Integer qty;         // 数量（1以上）
    private final ItemCategory category; // 任意。LUX なら贅沢品扱い
    private final Double weight;       // 1個あたり重量[kg]（0以上、任意）

    public CartItem(Double price, Integer qty, ItemCategory category, Double weight) {
      this.price = price;
      this.qty = qty;
      this.category = category;
      this.weight = weight;
    }
    public Double getPrice() { return price; }
    public Integer getQty() { return qty; }
    public ItemCategory getCategory() { return category; }
    public Double getWeight() { return weight; }
  }

  /** 副作用カウンタ。 */
  public static final class Counters {
    public int promoUsed = 0;
  }

  /** 計算オプション（未設定は既定値を使用）。 */
  public static final class Options {
    private Double taxRate;                 // 既定 0.10
    private Double freeShipThreshold;       // 既定 100
    private Double shipPerKg;               // 既定 2.5
    private String promoCode;               // 'SAVE10' のみ特別扱い
    private Integer dayOfWeek;              // 0=日, …, 3=水
    private Counters counters;              // 任意（副作用の観測用）

    public Double getTaxRate() { return taxRate; }
    public Options setTaxRate(double v) { this.taxRate = v; return this; }

    public Double getFreeShipThreshold() { return freeShipThreshold; }
    public Options setFreeShipThreshold(double v) { this.freeShipThreshold = v; return this; }

    public Double getShipPerKg() { return shipPerKg; }
    public Options setShipPerKg(double v) { this.shipPerKg = v; return this; }

    public String getPromoCode() { return promoCode; }
    public Options setPromoCode(String code) { this.promoCode = code; return this; }

    public Integer getDayOfWeek() { return dayOfWeek; }
    public Options setDayOfWeek(int dow) { this.dayOfWeek = dow; return this; }

    public Counters getCounters() { return counters; }
    public Options setCounters(Counters c) { this.counters = c; return this; }
  }

  /**
   * カートから最終支払額（>=0、小数2桁）を計算する。
   *
   * @param cart カート明細
   * @param opts オプション（null 可。未設定項目は既定値使用）
   * @return 最終支払額（>=0、小数2桁に丸め）
   */
  public static double computeOrderTotal(List<CartItem> cart, Options opts) {
    // 入力ガード：null/空なら 0（早期 return）
    if (cart == null || cart.isEmpty()) return 0.0;

    // オプションの正規化（未指定時のデフォルト値）
    final double taxRate = (opts != null && opts.getTaxRate() != null) ? opts.getTaxRate() : 0.10;
    final double freeShipThreshold = (opts != null && opts.getFreeShipThreshold() != null)
        ? opts.getFreeShipThreshold() : 100.0;
    final double shipPerKg = (opts != null && opts.getShipPerKg() != null) ? opts.getShipPerKg() : 2.5;
    final String promoCode = (opts != null) ? opts.getPromoCode() : null;
    final Integer dayOfWeek = (opts != null) ? opts.getDayOfWeek() : null;
    final Counters counters = (opts != null) ? opts.getCounters() : null;

    // 集計用
    double subtotal = 0.0;     // 小計：price * qty の総和
    double totalWeight = 0.0;  // 総重量：weight * qty の総和
    boolean hasLuxury = false; // 贅沢品を含むか

    // ループ：各明細を検査しながら集計
    for (CartItem it : cart) {
      // 欠落・未定義の行はスキップ
      if (it == null || it.getPrice() == null || it.getQty() == null) continue;
      // 不正値（負の価格、0以下の数量）はスキップ
      if (it.getPrice() < 0.0 || it.getQty() <= 0) continue;

      // 行金額
      double line = it.getPrice() * it.getQty();
      subtotal += line;

      // 重量（未指定は 0 扱い）
      double w = (it.getWeight() != null) ? it.getWeight() : 0.0;
      if (w > 0.0) totalWeight += w * it.getQty();

      // カテゴリが LUX ならフラグ
      if (it.getCategory() == ItemCategory.LUX) hasLuxury = true;
    }

    // 有効行が無ければ 0（早期 return）
    if (subtotal == 0.0) return 0.0;

    // 分岐1：贅沢品あり → 税率 +5%、なければ基本税率
    final double effectiveTax = hasLuxury ? taxRate + 0.05 : taxRate;

    // 分岐2：水曜割引（5%）
    final boolean isMidweek = Objects.equals(dayOfWeek, 3);
    double discount = isMidweek ? subtotal * 0.05 : 0.0;

    // 分岐3：プロモ 'SAVE10'（10%）。曜日割引と重ね不可 → 大きい方のみ
    if ("SAVE10".equals(promoCode)) {
      if (counters != null) counters.promoUsed += 1; // 副作用：カウンタ +1
      discount = Math.max(discount, subtotal * 0.10);
    }

    // 割引後に税を適用（2桁丸め）
    double taxed = Math.round((subtotal - discount) * (1.0 + effectiveTax) * 100.0) / 100.0;

    // 分岐4：税込が閾値以上なら送料無料、未満なら ceil(総重量)*単価
    double shipping = (taxed >= freeShipThreshold) ? 0.0
        : Math.ceil(totalWeight) * shipPerKg;

    // 最終額：負にならないよう 0 を下限に、2桁丸め
    double total = Math.max(0.0, Math.round((taxed + shipping) * 100.0) / 100.0);
    return total;
  }
}
