from __future__ import annotations

import ast
from typing import Any, Iterable, Optional

# parso
from parso import parse as parso_parse
from parso.python import tree as pytree


# ========= ユーティリティ =========

LITERAL_TYPE_MAP = {
    ast.List: "list",
    ast.Tuple: "tuple",
    ast.Set: "set",
    ast.Dict: "dict",
    ast.Constant: None,  # 値を見て判定（None/bool/int/float/str など）
}

CONSTRUCTOR_TYPE_MAP = {
    "list": "list",
    "tuple": "tuple",
    "set": "set",
    "dict": "dict",
    "int": "int",
    "float": "float",
    "str": "str",
    "bool": "bool",
}


def _type_from_ast_expr(expr: ast.AST) -> Optional[str]:
    """return式（の右辺）から型名を推定。わからなければ None。"""
    if isinstance(expr, ast.Constant):
        v = expr.value
        if v is None:
            return "None"
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, int):
            return "int"
        if isinstance(v, float):
            return "float"
        if isinstance(v, str):
            return "str"
        # bytes 等は必要なら追加
        return type(v).__name__

    for node_cls, tname in LITERAL_TYPE_MAP.items():
        if isinstance(expr, node_cls):
            return tname

    if isinstance(expr, ast.Call):
        # list(), dict(), ...
        f = expr.func
        if isinstance(f, ast.Name):
            return CONSTRUCTOR_TYPE_MAP.get(f.id)

    return None


def _collect_simple_assign_types(func_code: str) -> dict[str, str]:
    """
    関数本体中の「単純代入 x = <literal or constructor()>」を拾い、x -> 型名の辞書を返す。
    """
    result: dict[str, str] = {}
    try:
        m = ast.parse(func_code)
    except SyntaxError:
        return result

    class AssignVisitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> Any:
            # x = <expr> だけ（複数代入や属性代入は除外）
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tname = _type_from_ast_expr(node.value)
                if tname:
                    result[node.targets[0].id] = tname
            self.generic_visit(node)

    AssignVisitor().visit(m)
    return result


def _expr_code_of_return(ret_stmt: pytree.ReturnStmt) -> Optional[str]:
    """
    parsoの return 文ノードから右辺のテキストを抽出。
    値なし return は None。
    """
    code = ret_stmt.get_code().strip()
    # 例: "return", "return 1+2"
    if code == "return":
        return None
    # "return " の後ろを返す
    return code[7:].strip() if code.startswith("return ") else None


def _has_yield(func: pytree.Function) -> bool:
    # parso の補助 API（存在する前提）：iter_yield_exprs
    try:
        it = func.iter_yield_exprs()
        return any(True for _ in it)
    except AttributeError:
        # フォールバック（葉をなめる単純判定）
        return "yield" in func.get_code()


def _extract_return_annotation(func: pytree.Function) -> Optional[str]:
    """
    func の定義ヘッダから '-> ... :' の注釈部分を抽出（parso葉ノードを逐次走査）。
    """
    leaf = func.get_first_leaf()  # 'def' もしくは 'async'
    saw_arrow = False
    tokens: list[str] = []

    # 先頭の ':' に到達するまで 1 つずつ次の葉へ
    while leaf is not None and leaf.value != ":":
        if saw_arrow:
            tokens.append(leaf.value)
        if leaf.value == "->":
            saw_arrow = True
        leaf = leaf.get_next_leaf()

    ann = "".join(tokens).strip()
    return ann or None


def _wrap_async(annotation: str | None, is_async: bool) -> str:
    if not is_async:
        return annotation or "Unknown"
    # async def の場合：注釈は「await 後の型」を記す慣習。
    # 関数の実際の戻り値は coroutine なので、Coroutine[Any, Any, T] で包む。
    base = annotation or "Unknown"
    return f"Coroutine[Any, Any, {base}]"


# ========= メイン：関数の戻り型推定 =========

def infer_return_type_from_function(func: pytree.Function) -> str:
    """
    parso.python.tree.Function から戻り値の型名（文字列）を推定して返す。
    例: "int", "str", "list", "None", "Union[int, None]", "Generator[Any, None, T]" など。
    """
    code = func.get_code()

    # 1) async / async generator の判定
    is_async = code.lstrip().startswith("async def")
    if _has_yield(func):
        # ざっくり：async generator / sync generator
        return "AsyncGenerator[Any, Any]" if is_async else "Generator[Any, None]"

    # 2) 型注釈があれば最優先
    ann = _extract_return_annotation(func)
    if ann:
        return _wrap_async(ann, is_async)

    # 3) return 文から推定
    assign_types = _collect_simple_assign_types(code)
    types: set[str] = set()

    try:
        rets: Iterable[pytree.ReturnStmt] = func.iter_return_stmts()
    except AttributeError:
        rets = []  # parso のバージョン差で無い場合

    for r in rets:
        expr_src = _expr_code_of_return(r)
        if expr_src is None:
            types.add("None")
            continue
        try:
            expr_ast = ast.parse(expr_src, mode="eval").body
        except SyntaxError:
            types.add("Unknown")
            continue

        tname = _type_from_ast_expr(expr_ast)
        if tname:
            types.add(tname)
            continue

        # Name を単純代入で解決
        if isinstance(expr_ast, ast.Name):
            tname2 = assign_types.get(expr_ast.id)
            types.add(tname2 or "Unknown")
            continue

        # ここまで来たら不明
        types.add("Unknown")

    # return 文がなかったら（Pythonの仕様上 None）
    if not types:
        types.add("None")

    # 複数型なら Union 化
    if len(types) == 1:
        base = next(iter(types))
        return _wrap_async(base, is_async)
    # Unknown しか無いならそのまま
    if types == {"Unknown"}:
        return _wrap_async("Unknown", is_async)

    # Union の順序は見やすく整える
    order = ["None", "bool", "int", "float", "str", "bytes", "list", "tuple", "set", "dict", "Unknown"]
    sorted_types = sorted(types, key=lambda t: (order.index(t) if t in order else len(order), t))
    return _wrap_async(f"Union[{', '.join(sorted_types)}]", is_async)


# ========= 使い方（サンプル） =========
if __name__ == "__main__":
    src = '''
def f1():               # → None（returnなし）
    x = 1
    if x > 0:
        return
    x += 1

def f2() -> list[int]:  # → 注釈を優先
    return []

def f3():
    return 0.0          # → float

def f4():
    xs = []
    return xs           # → list（単純代入の追跡）

def f5():
    return dict()       # → dict

async def f6():
    return 1            # → Coroutine[Any, Any, int]

def f7():
    return (i for i in range(3))  # 複雑：Unknown と判定（簡易化）

def f8():
    return f6()
'''
    module = parso_parse(src)
    for func in module.iter_funcdefs():
        print(func.name.value, "=>", infer_return_type_from_function(func))
