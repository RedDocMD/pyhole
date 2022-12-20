from inspect import isbuiltin, isclass, isfunction, ismethod
from itertools import chain
from typing import Any, Tuple, Union
from .tracer import Tracer
from .db import KeywordDb, ObjectDb, Position
from .cache import FileCache
from .object import FormalParamKind, Function, Object
import ast
from termcolor import colored
import logging as lg
from types import FrameType, FunctionType, MethodType
import enum


fun_txt = colored("Fun", 'grey', 'on_white')
stmt_txt = colored("Stmt", 'grey', 'on_yellow')
kwd_txt = colored("Valid keywords", 'grey', 'on_red', attrs=['bold'])


def get_position(frame):
    lineno = frame.f_lineno
    filename = frame.f_code.co_filename
    return Position(filename, lineno)


class FunctionNotFound(Exception):
    pass


def nearest_enclosing_function(pos: Position, db: ObjectDb):
    file_obs = db.file_fn_obs(pos.filename)
    idx = 0
    while idx < len(file_obs):
        lineno, ob = file_obs[idx]
        if lineno > pos.start_line:
            idx += 1
        else:
            return ob
    return None


def expr_call_expressions(expr):
    def join_find(lst):
        return list(chain.from_iterable(map(expr_call_expressions, lst)))

    match expr:
        case ast.Call():
            return [expr]
        case ast.BoolOp(values=values):
            return join_find(values)
        case ast.NamedExpr(value=value):
            return expr_call_expressions(value)
        case ast.BinOp(left=left, right=right):
            return expr_call_expressions(left) + expr_call_expressions(right)
        case ast.UnaryOp(operand=operand):
            return expr_call_expressions(operand)
        case ast.IfExp(test=test, body=body, orelse=orelse):
            return join_find([test, body, orelse])
        case ast.Dict(keys=keys, values=values):
            return join_find(keys + values)
        case ast.Set(elts=elts):
            return join_find(elts)
        # Ignore: ListComp, SetComp, DictComp, GeneratorExpr
        case ast.Await(value=value):
            return expr_call_expressions(value)
        # Ignore: Yield, YieldFrom
        case ast.Compare(left=left, comparators=rest):
            return join_find([left] + rest)
        case ast.Subscript(value=value, slice=sl):
            return join_find([value, sl])
        case ast.Starred(value=value):
            return expr_call_expressions(value)
        case ast.List(elts=elts):
            return join_find(elts)
        case ast.Tuple(elts=elts):
            return join_find(elts)
        case ast.Slice(lower=lower, upper=upper, step=step):
            return join_find([lower, upper, step])
        case _:
            return []


def stmt_call_expressions(stmt):
    match stmt:
        case ast.Return(value=expr):
            return expr_call_expressions(expr)
        case ast.Assign(value=expr):
            return expr_call_expressions(expr)
        case ast.AugAssign(value=expr):
            return expr_call_expressions(expr)
        case ast.AnnAssign(value=expr):
            return expr_call_expressions(expr)
        case ast.Expr(value=expr):
            return expr_call_expressions(expr)
        case _:
            return []


def extract_keywords(kwds):
    ids = []
    for kwd in kwds:
        if kwd.arg:
            ids.append(str(kwd.arg))
    return ids


class SimpleKeywordTracer(Tracer):
    db: ObjectDb
    kw_fns: set[Object]
    fc: FileCache

    def __init__(self, db: ObjectDb, kw_fns: ObjectDb):
        super().__init__()
        self.db = db
        self.kw_fns = set(kw_fns.db.values())
        self.fc = FileCache()
        # All call positions
        self.call_stack = []
        # All call positions in db (along with object)
        self.aux_call_stack = []
        # All call positions for functions with kwargs
        self.kwfn_stack = []
        # Call_exprs must be sorted in terms of call order
        self.call_exprs = []
        self.doing_call = False

    def trace_call(self, frame: FrameType):
        pos = get_position(frame)
        self.call_stack.append(pos)
        if pos in self.db:
            ob = self.db[pos]
            self.aux_call_stack.append((pos, ob))
            if ob in self.kw_fns:
                print(fun_txt, ob, ob.source_span)
                if self.call_exprs:
                    fn = self.call_exprs[-1]
                    kwds = extract_keywords(fn.keywords)
                    if len(kwds) > 0:
                        print(kwd_txt, ', '.join(kwds))
                self.kwfn_stack.append(ob)
        if self.call_exprs:
            self.call_exprs.pop()
        if self.doing_call and not self.call_exprs:
            self.doing_call = False

    def _update_call_expressions(self, stmt):
        call_exprs = stmt_call_expressions(stmt)
        if call_exprs:
            self.doing_call = True
            self.call_exprs.extend(call_exprs)

    def trace_line(self, frame: FrameType):
        if self.doing_call:
            return
        if not self.aux_call_stack:
            return
        call_pos, call_ob = self.aux_call_stack[-1]
        if not isinstance(call_ob, Function):
            return
        lg.debug('%s: %s', call_ob, call_pos)
        pos = get_position(frame)
        enc_ob = nearest_enclosing_function(pos, self.db)
        if not enc_ob:
            lg.critical("enc_ob is None, for %s", pos)
        if enc_ob != call_ob:
            return
        lg.debug(call_ob.stmts)
        self._update_call_expressions(call_ob.stmts[frame.f_lineno])

        # TODO: Perform dictionary access analysis
        # TODO: Perform mutation analysis
        if not self.kwfn_stack == 0:
            return
        kw_ob = self.kwfn_stack[-1]
        if kw_ob != call_ob:
            return
        if enc_ob is None or enc_ob != kw_ob:
            return

    def trace_return(self, frame: FrameType):
        call_pos = self.call_stack[-1]
        self.call_stack.pop()
        if len(self.aux_call_stack) > 0:
            call_ob, pos = self.aux_call_stack[-1]
            if pos == call_pos:
                self.aux_call_stack.pop()
                if len(self.kwfn_stack) != 0 and self.kwfn_stack[-1] == call_ob:
                    self.kwfn_stack.pop()


def split_attr_expr(expr: ast.Attribute):
    parts = []
    value = expr.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    elif isinstance(value, ast.Constant):
        parts.append(value)
    elif isinstance(value, ast.Attribute):
        others = split_attr_expr(value)
        parts.extend(others)
    elif isinstance(value, ast.Call):
        parts.append(value)
    elif isinstance(value, ast.Subscript):
        parts.append(value)
    else:
        raise RuntimeError(f"Got {value} as value for ast.Attribute")
    parts.append(expr.attr)
    return parts


class FunctionKind(enum.Enum):
    LOC = 0
    GLOB = 1
    BUILTIN = 2
    NOT_FOUND = 3
    UNKNOWN = 4


class SymbolKind(enum.Enum):
    LOC = 0
    GLOB = 1
    BUILTIN = 2
    NOT_FOUND = 3

    def to_function_type(self) -> FunctionKind:
        match self:
            case SymbolKind.LOC:
                return FunctionKind.LOC
            case SymbolKind.GLOB:
                return FunctionKind.GLOB
            case SymbolKind.BUILTIN:
                return FunctionKind.BUILTIN
            case SymbolKind.NOT_FOUND:
                return FunctionKind.NOT_FOUND


class SymbolTable:
    loc: dict[str, Any]
    glob: dict[str, Any]
    builtins: dict[str, Any]

    def __init__(self, loc: dict[str, Any], glob: dict[str, Any], builtins: dict[str, Any]):
        self.loc = loc
        self.glob = glob
        self.builtins = builtins

    def lookup(self, name: str) -> Tuple[Any, SymbolKind]:
        if name in self.loc:
            return self.loc[name], SymbolKind.LOC
        elif name in self.glob:
            return self.glob[name], SymbolKind.GLOB
        elif name in self.builtins:
            return self.builtins[name], SymbolKind.BUILTIN
        else:
            return None, SymbolKind.NOT_FOUND

    def __str__(self) -> str:
        return f'locals = {self.loc.keys()}\nglobals = {self.glob.keys()}\nbuiltins = {self.builtins.keys()}'


def lookup_fn(ob: Any, names: list[str]) -> Any:
    thing = getattr(ob, names[0])
    if len(names) == 1:
        return thing
    return lookup_fn(thing, names[1:])


def find_called_fn(expr: ast.Expression, sym_tab: SymbolTable) -> Tuple[Any, FunctionKind]:
    match expr:
        case ast.Name(id=name):
            # TODO: Check the expr_context
            fn, kind = sym_tab.lookup(name)
            if not fn:
                lg.error("%s for Name not found in loc or glob", name)
            return fn, kind.to_function_type()
        case ast.Attribute(value=expr):
            # TODO: Check the expr_context
            parts = split_attr_expr(expr)
            for part in parts:
                if not isinstance(part, str):
                    return None, FunctionKind.UNKNOWN
            name = parts[0]
            base, kind = sym_tab.lookup(name)
            if base is None:
                lg.error(
                    "%s for Attribute not found in symbol table %s", name, parts)
                return None, FunctionKind.NOT_FOUND
            fn = lookup_fn(base, parts[1:])
            return fn, kind.to_function_type()
    return None, FunctionKind.NOT_FOUND


def resolve_function(fn, kind):
    if fn is None:
        return None, kind
    if isclass(fn):
        dc = fn.__dict__
        if "__init__" in dc:
            return dc["__init__"], kind
        return None, FunctionKind.UNKNOWN
    if isbuiltin(fn):
        return fn, FunctionKind.BUILTIN
    if not isfunction(fn) and not ismethod(fn):
        raise RuntimeError(f"{fn} was expected to be a function")
    return fn, kind


class KeywordValKind(enum.Enum):
    PARENT = 0
    CHILD = 1

    def __str__(self) -> str:
        match self:
            case KeywordValKind.PARENT:
                return "PARENT"
            case KeywordValKind.CHILD:
                return "CHILD"


class KeywordVal:
    kind: KeywordValKind
    name: str

    def __init__(self, kind: KeywordValKind, name: str) -> None:
        self.kind = kind
        self.name = name

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


def _enc_ob_pos(frame: FrameType) -> Position:
    filename = frame.f_code.co_filename
    lineno = frame.f_code.co_firstlineno
    return Position(filename, lineno)


class CallTracer(Tracer):
    dbs: list[ObjectDb]
    kw_fns: list[ObjectDb]
    kwd_db: KeywordDb

    def __init__(self, dbs: ObjectDb | list[ObjectDb],
                 kw_fns: ObjectDb | list[ObjectDb],
                 kwd_db: KeywordDb) -> None:
        super().__init__()
        if not isinstance(dbs, list):
            self.dbs = [dbs]
        else:
            self.dbs = dbs
        if not isinstance(kw_fns, list):
            self.kw_fns = [kw_fns]
        else:
            self.kw_fns = kw_fns
        self.kwd_db = kwd_db

    def _is_kwd_fn(self, fn: Function) -> bool:
        return any(map(lambda dt: dt.has_ob(fn), self.kw_fns))

    def _lookup_fn(self, fn: Union[FunctionType, MethodType]) -> Function | None:
        for db in self.dbs:
            out = db.lookup_fn(fn)
            if out:
                assert(isinstance(out, Function))
                return out
        return None

    def _enc_fn(self, frame: FrameType) -> Function | None:
        pos = _enc_ob_pos(frame)
        for db in self.dbs:
            if pos in db:
                ob = db[pos]
                if isinstance(ob, Function):
                    return ob
        return None

    def _find_keyword_params(self,
                             par_fn: Function,
                             child_fn: Function,
                             call_expr: ast.Call) -> list[KeywordVal]:
        par_has_kw = self._is_kwd_fn(par_fn)
        child_has_kw = self._is_kwd_fn(child_fn)

        res: list[KeywordVal] = []

        params = child_fn.get_formal_params()
        posonly_params = list(
            filter(lambda p: p.kind == FormalParamKind.POSONLY, params))
        norm_params = list(
            filter(lambda p: p.kind == FormalParamKind.NORMAL and p.name != "self", params))
        kwonly_params = list(
            filter(lambda p: p.kind == FormalParamKind.KWONLY, params))

        # Figure out child kw
        if child_has_kw:
            kwds = call_expr.keywords
            param_names = list(
                filter(lambda p: p.name, norm_params + kwonly_params))
            for kwd in kwds:
                name = kwd.arg
                if name and name not in param_names:
                    res.append(KeywordVal(KeywordValKind.CHILD, name))
                # TODO: Extract information from the fun(**args) case.

        # Figure out par kw
        if par_has_kw:
            par_kw_name = par_fn.get_kwargs_name()
            kwds = call_expr.keywords
            args = call_expr.args

            targ_kwd_found = False
            star_pos_found = False
            for kwd in kwds:
                if not kwd.arg and isinstance(kwd.value, ast.Name) and kwd.value.id == par_kw_name:
                    targ_kwd_found = True
                    break
            for arg in args:
                if isinstance(arg, ast.Starred):
                    star_pos_found = True
                    break

            if targ_kwd_found:
                kwds_covered = list(map(lambda k: k.arg,
                                        filter(lambda k: k.arg, kwds)))

                if not star_pos_found:
                    pos_covered_cnt = len(args)
                else:
                    pos_covered_cnt = len(posonly_params) + len(norm_params)

                # First remove all positional params
                norm_params_covered = max(0, min(
                    len(norm_params), pos_covered_cnt - len(posonly_params)))
                # Then remove all normal params with default values or is in kwds_covered
                # TODO: Strict mode for required keyword arguments
                norm_params_left = list(
                    filter(lambda p: p.name not in kwds_covered,
                           norm_params[norm_params_covered:]))
                # Find kwonly args that have not been covered
                kwonly_params_left = list(
                    filter(lambda p: p.name not in kwds_covered, kwonly_params))

                # That all must be accounted for by **kwargs
                for param in chain(norm_params_left, kwonly_params_left):
                    res.append(KeywordVal(KeywordValKind.PARENT, param.name))

        return res

    def trace_line(self, frame: FrameType):
        enc_ob = self._enc_fn(frame)
        ln = frame.f_lineno
        if not enc_ob:
            return
        if ln not in enc_ob.stmts:
            return
        stmt = enc_ob.stmts[ln]
        call_exprs = stmt_call_expressions(stmt)
        if not call_exprs:
            return
        sym_tab = SymbolTable(
            frame.f_locals, frame.f_globals, frame.f_builtins)
        for call_expr in call_exprs:
            called_fn, kind = resolve_function(
                *find_called_fn(call_expr.func, sym_tab))
            if called_fn is not None and kind != FunctionKind.BUILTIN:
                fn_ob = self._lookup_fn(called_fn)
                if fn_ob:
                    lg.info("Parent: %s", enc_ob)
                    lg.info("Child: %s", fn_ob)
                    lg.info("Kwd args: %s",
                            list(map(lambda arg: arg.arg, call_expr.keywords)))
                    kwds = self._find_keyword_params(enc_ob, fn_ob, call_expr)
                    lg.info("Kwds: [%s]", ', '.join(map(str, kwds)))
                    for kwd in kwds:
                        fn = enc_ob if kwd.kind == KeywordValKind.PARENT else fn_ob
                        self.kwd_db.append_possibility(fn, kwd.name)
            elif called_fn is None and kind != FunctionKind.UNKNOWN:
                pos = get_position(frame)
                lg.error("called_fn not found at %s", pos)
