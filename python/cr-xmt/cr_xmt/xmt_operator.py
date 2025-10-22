from __future__ import annotations
from typing import Iterable, Tuple
from cosmic_ray.operators.operator import Operator
import parso
from parso.python import tree as pytree

def _suite_with_return(indent: str, expr: str) -> pytree.PythonNode:
    # 簡単なテンプレートをパースして suite ノードだけ取り出す
    code = f"def _():\n{indent}return {expr}\n"
    mod = parso.parse(code)
    return mod.children[0].children[-1]  # suite

def _suite_empty(indent: str) -> pytree.PythonNode:
    code = f"def _():\n{indent}pass\n"
    mod = parso.parse(code)
    return mod.children[0].children[-1]  # suite

# 関数内に 'yield' があれば generator と見なして空本体に
def _has_yield(n):
    if not hasattr(n, "children"):
        return False
    for ch in n.children:
        if getattr(ch, "value", None) == "yield":
            return True
        if _has_yield(ch):
            return True
    return False

class XmtFunctionReturn(Operator):
    """XMT最小版: 関数/メソッドの本体(suite)を 'return None' へ置換。
       （generatorは空本体）"""
    def examples(self):  # -> Iterable[Tuple[str, str]]
        """このオペレータが行う変異の最小例を返す。"""
        # 通常関数
        yield (
            "def foo():\n    return 1\n",
            "def foo():\n    return None\n",
        )
        # generator は空本体に
        yield (
            "def gen():\n    yield 1\n",
            "def gen():\n    pass\n",
        )

    def mutation_positions(self, node) -> Iterable[Tuple[Tuple[int,int], Tuple[int,int]]]:
        # parso の Function ノードのみ対象（lambdaは対象外）
        # cosmic-ray init 時の対象列挙時に実行される
        if isinstance(node, pytree.Function):
            suite = node.children[-1]
            if isinstance(suite, pytree.PythonNode) and suite.type == "suite":
                yield (suite.start_pos, suite.end_pos)

    def mutate(self, node, index):
        assert isinstance(node, pytree.Function)
        suite: pytree.PythonNode = node.children[-1]  # type: ignore[assignment]
        # 既存のインデントを推定（suite 先頭のカラム）
        first_leaf = suite.get_first_leaf()
        indent = " " * (first_leaf.column if first_leaf else 4)
        new_suite = _suite_empty(indent) if _has_yield(suite) else _suite_with_return(indent, "None")

        # suite を差し替えた新しい Function ノードを返す
        new_children = list(node.children)
        new_children[-1] = new_suite
        node.children = new_children
        return node
