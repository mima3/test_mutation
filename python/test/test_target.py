# test_compute_order_total.py
import pytest
from src.target import compute_order_total, Target


class TestComputeOrderTotal:
    def test_empty_list_returns_zero(self):
        assert compute_order_total([]) == 0.0

    def test_non_list_returns_zero(self):
        assert compute_order_total(None) == 0.0  # type: ignore[arg-type]

    def test_invalid_rows_are_skipped_and_all_invalid_returns_zero(self):
        cart = [
            None,                               # 行欠落
            {"price": None, "qty": 1},          # price 欠落
            {"price": 100, "qty": None},        # qty 欠落
            {"price": -5, "qty": 2},            # 価格負
            {"price": 10, "qty": 0},            # 数量0
        ]
        assert compute_order_total(cart) == 0.0

    def test_normal_case_with_shipping(self):
        cart = [
            {"price": 20, "qty": 2},
            {"price": 15, "qty": 1, "weight": 0.4},  # 重量>0 の経路
        ]
        opts = {"taxRate": 0.1, "freeShipThreshold": 100, "shipPerKg": 3}
        # 小計=55 → 税込=60.5、重量=0.4→ceil=1 → 送料=3 → 合計=63.5
        assert compute_order_total(cart, opts) == 63.5

    def test_luxury_flag_adds_tax_and_wednesday_discount_applies(self):
        cart = [{"price": 100, "qty": 1, "category": "lux", "weight": 1.2}]
        opts = {"dayOfWeek": 3, "taxRate": 0.1, "freeShipThreshold": 120, "shipPerKg": 2.5}
        # 例示値：114.25
        assert compute_order_total(cart, opts) == 114.25

    def test_promo_save10_beats_wednesday_and_increments_counter(self):
        counters = {"promoUsed": 0}
        cart = [
            {"price": 90, "qty": 1, "weight": 0.5},
            {"price": 30, "qty": 1},
        ]
        opts = {"promoCode": "SAVE10", "counters": counters, "freeShipThreshold": 110}
        # 例示値：118.8、promoUsed は +1
        assert compute_order_total(cart, opts) == 118.8
        assert counters["promoUsed"] == 1

    def test_shipping_threshold_rules(self):
        # 税率0にして税込=小計（丸め影響を避ける）
        base = {"taxRate": 0.0, "shipPerKg": 5.0, "freeShipThreshold": 100.0}

        # 未満（99.99）→ 送料発生（重量 0.4 → ceil=1 → 5）
        assert compute_order_total([{"price": 99.99, "qty": 1, "weight": 0.4}], base) == 104.99

        # ちょうど（100）→ 送料無料
        assert compute_order_total([{"price": 100, "qty": 1, "weight": 10}], base) == 100.0

        # 超え（120）→ 送料無料
        assert compute_order_total([{"price": 60, "qty": 2, "weight": 10}], base) == 120.0

    @pytest.mark.parametrize(
        "w, expected",
        [
            (0.0, 10.0),   # ceil(0)=0 → 送料0
            (0.01, 13.0),  # ceil(0.01)=1 → 送料3
            (0.99, 13.0),  # ceil(0.99)=1 → 送料3
            (1.0, 13.0),   # ceil(1)=1 → 送料3
        ],
    )
    def test_weight_ceiling_edges(self, w, expected):
        opts = {"taxRate": 0.0, "freeShipThreshold": 9999.0, "shipPerKg": 3.0}
        assert compute_order_total([{"price": 10, "qty": 1, "weight": w}], opts) == expected

    def test_no_promo_and_not_wednesday_and_no_lux(self):
        cart = [
            {"price": 50, "qty": 1, "category": "normal", "weight": 0},
            {"price": 10, "qty": 2},  # subtotal=70
        ]
        opts = {"taxRate": 0.08, "dayOfWeek": 2, "freeShipThreshold": 100, "shipPerKg": 4}
        # 割引0、税8% → 税込=75.6、重量=0 → 送料0 → 合計=75.6
        assert compute_order_total(cart, opts) == 75.6

    def test_weight_missing_or_nonpositive_and_category_missing(self):
        cart = [
            {"price": 10, "qty": 1},           # weight 未指定（0扱い）、category 未指定
            {"price": 5, "qty": 2, "weight": 0},  # weight 0（加算しない）
        ]
        opts = {"taxRate": 0.1, "freeShipThreshold": 9999, "shipPerKg": 10}
        # subtotal=20、tax=10% → 22、重量=0 → 送料0 → 合計22
        assert compute_order_total(cart, opts) == 22.0

class TestTarget:
    def test_is_adult(self):
        obj = Target()
        assert obj.is_adult(20) == True

    def test_coroutine(self):
        obj = Target()
        act = obj.coroutine([])
        print(act)
