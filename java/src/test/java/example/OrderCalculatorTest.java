package example;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Arrays;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import example.OrderCalculator.CartItem;
import example.OrderCalculator.Counters;
import example.OrderCalculator.ItemCategory;
import example.OrderCalculator.Options;

@DisplayName("computeOrderTotal の単体テスト（ステートメントカバレッジ重視）")
class OrderCalculatorTest {

  private static void assertMoney(double expected, double actual) {
    assertEquals(expected, actual, 1e-9);
  }

  @Test
  @DisplayName("空配列は 0 を返す（早期return）")
  void emptyCartReturnsZero() {
    double total = OrderCalculator.computeOrderTotal(List.of(), null);
    assertMoney(0.0, total);
  }

  @Test
  @DisplayName("配列以外（null）は 0 を返す（早期return）")
  void nullCartReturnsZero() {
    double total = OrderCalculator.computeOrderTotal(null, null);
    assertMoney(0.0, total);
  }

  @Test
  @DisplayName("不正行（欠落・負値・数量0）はスキップされ、すべて無効なら 0")
  void invalidLinesAreSkippedAndResultZero() {
    List<CartItem> cart = Arrays.asList(
        (CartItem) null,                       // 行欠落（null OK）
        new CartItem(null, 1, null, null),     // price 欠落
        new CartItem(100.0, null, null, null), // qty 欠落
        new CartItem(-5.0, 2, null, null),     // 価格負
        new CartItem(10.0, 0, null, null)      // 数量0
    );

    double total = OrderCalculator.computeOrderTotal(cart, null);
    assertEquals(0.0, total, 1e-9);
  }

  @Test
  @DisplayName("通常ケース：送料あり（例示と同じ数値）")
  void normalCaseWithShipping() {
    List<CartItem> cart = List.of(
        new CartItem(20.0, 2, ItemCategory.NORMAL, null),
        new CartItem(15.0, 1, ItemCategory.NORMAL, 0.4)
    );
    Options opts = new Options()
        .setTaxRate(0.1)
        .setFreeShipThreshold(100.0)
        .setShipPerKg(3.0);

    // 小計=55 → 税込=60.5、重量=0.4→ceil=1 → 送料=3 → 合計=63.5
    double total = OrderCalculator.computeOrderTotal(cart, opts);
    assertMoney(63.5, total);
  }

  @Test
  @DisplayName("贅沢品フラグで税率+5%（水曜5%引きも適用）")
  void luxuryAndMidweekDiscount() {
    List<CartItem> cart = List.of(
        new CartItem(100.0, 1, ItemCategory.LUX, 1.2)
    );
    Options opts = new Options()
        .setDayOfWeek(3)                 // 水曜
        .setTaxRate(0.1)
        .setFreeShipThreshold(120.0)
        .setShipPerKg(2.5);

    double total = OrderCalculator.computeOrderTotal(cart, opts);
    assertMoney(114.25, total);          // 例示値
  }

  @Test
  @DisplayName("プロモ SAVE10 は曜日割引より強い（大きい方のみ）。副作用カウンタが +1 される")
  void promoSave10BeatsMidweekAndIncrementsCounter() {
    Counters counters = new Counters();
    List<CartItem> cart = List.of(
        new CartItem(90.0, 1, ItemCategory.NORMAL, 0.5),
        new CartItem(30.0, 1, ItemCategory.NORMAL, null)
    );
    Options opts = new Options()
        .setPromoCode("SAVE10")
        .setCounters(counters)
        .setFreeShipThreshold(110.0);

    double total = OrderCalculator.computeOrderTotal(cart, opts);
    assertMoney(118.8, total);
    assertEquals(1, counters.promoUsed);
  }

  @Test
  @DisplayName("送料の閾値：税込が閾値未満なら送料あり、ちょうど・超えなら送料無料")
  void shippingThresholdCases() {
    Options base = new Options()
        .setTaxRate(0.0)            // 税率0にして税込=小計
        .setShipPerKg(5.0)
        .setFreeShipThreshold(100.0);

    // 未満（99.99）→ 送料あり（重量0.4 → ceil=1 → 5）
    double a = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(99.99, 1, ItemCategory.NORMAL, 0.4)), base);
    assertMoney(104.99, a);

    // ちょうど（100）→ 送料無料
    double b = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(100.0, 1, ItemCategory.NORMAL, 10.0)), base);
    assertMoney(100.0, b);

    // 超え（120）→ 送料無料
    double c = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(60.0, 2, ItemCategory.NORMAL, 10.0)), base);
    assertMoney(120.0, c);
  }

  @Test
  @DisplayName("重量の切り上げ境界を確認（0, 0.01, 0.99, 1.0）")
  void shippingWeightRoundingBoundaries() {
    Options opts = new Options()
        .setTaxRate(0.0)
        .setFreeShipThreshold(9999.0) // 送料無料にならないよう高閾値
        .setShipPerKg(3.0);

    // 0.00 kg → ceil(0)=0 → 送料0
    double t0 = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(10.0, 1, ItemCategory.NORMAL, 0.0)), opts);
    assertMoney(10.0, t0);

    // 0.01 kg → ceil(0.01)=1 → 送料3
    double t1 = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(10.0, 1, ItemCategory.NORMAL, 0.01)), opts);
    assertMoney(13.0, t1);

    // 0.99 kg → ceil(0.99)=1 → 送料3
    double t2 = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(10.0, 1, ItemCategory.NORMAL, 0.99)), opts);
    assertMoney(13.0, t2);

    // 1.00 kg → ceil(1)=1 → 送料3
    double t3 = OrderCalculator.computeOrderTotal(
        List.of(new CartItem(10.0, 1, ItemCategory.NORMAL, 1.0)), opts);
    assertMoney(13.0, t3);
  }

  @Test
  @DisplayName("プロモなし・水曜でもない（割引0）の経路を通す（hasLuxury=false 側の税率）")
  void noPromoNoMidweek() {
    List<CartItem> cart = List.of(
        new CartItem(50.0, 1, ItemCategory.NORMAL, 0.0),
        new CartItem(10.0, 2, ItemCategory.NORMAL, null) // subtotal=70
    );
    Options opts = new Options()
        .setTaxRate(0.08)
        .setDayOfWeek(2)  // 火
        .setFreeShipThreshold(100.0)
        .setShipPerKg(4.0);

    double total = OrderCalculator.computeOrderTotal(cart, opts);
    assertMoney(75.6, total);
  }

  @Test
  @DisplayName("行スキップの分岐（weight 未指定・<=0）とカテゴリ未指定を通す")
  void weightMissingOrZeroAndCategoryMissing() {
    List<CartItem> cart = List.of(
        new CartItem(10.0, 1, null, null),   // weight 未指定（0扱い）、category 未指定
        new CartItem(5.0, 2, null, 0.0)      // weight 0（加算しない）
    );
    Options opts = new Options()
        .setTaxRate(0.1)
        .setFreeShipThreshold(9999.0)
        .setShipPerKg(10.0);

    // subtotal=20、tax=10% → 22、重量=0 → 送料0 → 合計22
    double total = OrderCalculator.computeOrderTotal(cart, opts);
    assertMoney(22.0, total);
  }
}
