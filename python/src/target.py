from __future__ import annotations
from typing import TypedDict, Literal, Optional
import math


ItemCategory = Literal['food', 'lux', 'normal']


class CartItem(TypedDict, total=False):
    """1行の明細"""
    price: float                 # 単価（0以上）。欠落・不正はスキップ。
    qty: float                   # 数量（1以上）。欠落・不正はスキップ。
    category: ItemCategory       # 任意。'lux' を含むと贅沢品扱い（税率+5%）。
    weight: float                # 1個あたり重量[kg]（0以上、任意）。送料計算に使用。


class Counters(TypedDict):
    promoUsed: int               # プロモコード適用回数（副作用で +1）。


class Options(TypedDict, total=False):
    taxRate: float               # 基本税率（0.10 = 10%）。既定: 0.10
    freeShipThreshold: float     # 税込金額がこの閾値以上なら送料0円。既定: 100
    shipPerKg: float             # 送料の単価（kgあたり、重量は切り上げ）。既定: 2.5
    promoCode: str               # 'SAVE10' なら10%引き（曜日割引と重ね不可：大きい方のみ適用）
    dayOfWeek: int               # 曜日（0=日, 1=月, …, 3=水）。水曜は5%引き。
    counters: Counters           # 副作用を観測するためのカウンタ。


def _js_round2(x: float) -> float:
    """
    JS の Math.round(x*100)/100 を正数領域で再現（0.005 以上を切り上げ）。
    仕様上、今回の金額・重量は 0 以上なのでこれで十分。
    """
    return math.floor(x * 100.0 + 0.5) / 100.0


def compute_order_total(cart: list[CartItem], opts: Optional[Options] = None) -> float:
    """
    カートから最終支払額（>=0、少数2桁）を計算する。

    仕様:
      - 不正行（price欠落/負、qty欠落/<=0）はスキップ。
      - 贅沢品を1つでも含むと税率に +5%。
      - 水曜（dayOfWeek===3）は小計の5%引き。
      - プロモ 'SAVE10' は小計の10%引き。曜日割引と**重ね不可**（大きい方のみ適用）。
      - 割引適用後に税計算。丸めは都度「JS風の2桁丸め」。
      - 税込金額が閾値以上なら送料0円、未満なら ceil(総重量[kg]) * shipPerKg。
      - 'SAVE10' 適用時に counters.promoUsed を +1（副作用）。
      - 空配列や有効行がない場合は 0 を返す（早期return）。

    戻り値:
      最終支払額（>=0、小数2桁に丸め）。
    """
    if not isinstance(cart, list) or len(cart) == 0:
        return 0.0

    o = opts or {}
    tax_rate = o.get('taxRate', 0.10)
    free_ship_threshold = o.get('freeShipThreshold', 100.0)
    ship_per_kg = o.get('shipPerKg', 2.5)

    subtotal = 0.0
    total_weight = 0.0
    has_luxury = False

    for item in cart:
        if not item:
            continue
        price = item.get('price')
        qty = item.get('qty')
        if price is None or qty is None:
            continue
        if price < 0 or qty <= 0:
            continue

        line = float(price) * float(qty)
        subtotal += line

        w = float(item.get('weight', 0.0) or 0.0)
        if w > 0:
            total_weight += w * float(qty)

        if item.get('category') == 'lux':
            has_luxury = True

    if subtotal == 0.0:
        return 0.0

    effective_tax = (tax_rate + 0.05) if has_luxury else tax_rate

    is_midweek = (o.get('dayOfWeek') == 3)  # 0=Sun ... 3=Wed
    discount = subtotal * 0.05 if is_midweek else 0.0

    if o.get('promoCode') == 'SAVE10':
        # 副作用カウント
        counters = o.get('counters')
        if isinstance(counters, dict) and isinstance(counters.get('promoUsed'), int):
            counters['promoUsed'] += 1
        discount = max(discount, subtotal * 0.10)

    # 割引後に税適用
    taxed = _js_round2((subtotal - discount) * (1.0 + effective_tax))

    shipping = 0.0 if taxed >= free_ship_threshold else math.ceil(total_weight) * ship_per_kg

    total = max(0.0, _js_round2(taxed + shipping))
    return total

class Target:
    def is_adult(self,age):
        return age >= 20

    def add(self,x, y):
        return x + y

    def coroutine(self,items):
        for item in items:
            yield item
