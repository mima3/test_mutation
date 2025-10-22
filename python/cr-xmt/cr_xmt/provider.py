from .xmt_operator import XmtFunctionReturn

class Provider:
    _operators = {"xmt/function-return": XmtFunctionReturn}
    def __iter__(self): return iter(self._operators)
    def __getitem__(self, name): return self._operators[name]