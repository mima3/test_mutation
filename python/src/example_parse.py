import parso
# https://github.com/davidhalter/parso/blob/master/parso/python/tree.py#L534

code_error = """
def func(x:int, y:int) -> int:
    # エラー
    return x:
"""

code1 = """
def func(x:int, y:int) -> int:
    # コメント
    return x + y # 戻り
"""
code2 = """
def func(x, y):
    return x + y
"""
code3 = """
def func(x):
    if x == 0:
        return "NONE"
    elif x == 1:
        return 1234
    else:
        return None
"""
code4 = """
def func():
    yield 1
    yield 2
    yield 3
"""
code5 = """
async def func(x):
    return x+1
"""

code6 = """
def func(
    a, b=1,            # 1) 位置/キーワード両用（positional-or-keyword）
    /,                 # ← 2) これより左は「位置専用（positional-only）」になる区切り
    c=5, d=2,            # 1) 続き
    *args,             # 3) 可変長位置（var-positional）
    e, f=3,            # 4) キーワード専用（keyword-only） … * の右側
    **kwargs           # 5) 可変長キーワード（var-keyword）
):
    print(a, b, c, d, args, e, f, kwargs)
"""

def dump(code):
    grammar = parso.load_grammar(version="3.11")
    module = grammar.parse(code)
    expr = module.children[0]
    async_flg = False
    print('===========================')
    if not isinstance(expr, parso.python.tree.Function):
        expr = expr.children[1]
        async_flg = True
    # expr.name: parso.python.tree.Name
    # for i, child in enumerate(expr.children):
    #    print("  ", i, child, type(child))
    print(expr)
    print("async_flg:", async_flg)
    print("name:", expr.name.value, expr.name.line, expr.name.column)
    print('iter_errors:')
    for issue in grammar.iter_errors(module):
        # parso.normalizer.Issue
        print("  ", issue.code, issue.message, issue.start_pos, issue.end_pos)
    parameters = expr.children[2]
    print('parameters:', parameters.type)
    for child in parameters.children:
        print('  ', child)

    print('iter_return_stmts:')
    for child in expr.iter_return_stmts():
        print("  ", child)

    print('iter_yield_exprs:')
    for child in expr.iter_yield_exprs():
        print("  ", child)

dump(code6)
#dump(code2)
#dump(code3)
#dump(code4)
