from inspect import isbuiltin, isclass, isfunction, ismethod
from typing import Any, Tuple
from .tracer import Tracer
from .db import ObjectDb, Position
from .cache import FileCache
from .object import Function
import ast
from termcolor import colored
import logging as lg
from types import FrameType
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


# TODO: Handle all valid expressions
def expr_call_expressions(expr):
    match expr:
        case ast.Call():
            return [expr]
        case _:
            return []


# TODO: Handle all valid statements
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
        case ast.Expr(expr=expr):
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
    kw_fns: ObjectDb
    fc: FileCache

    def __init__(self, db: ObjectDb, kw_fns: ObjectDb):
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
        case ast.Attribute(value=value, attr=attr):
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


class CallTracer(Tracer):
    db: ObjectDb

    def __init__(self, db: ObjectDb):
        self.db = db

    def trace_line(self, frame: FrameType):
        pos = get_position(frame)
        enc_ob = nearest_enclosing_function(pos, self.db)
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
            # lg.debug(pos)
            called_fn, kind = resolve_function(
                *find_called_fn(call_expr.func, sym_tab))
            if called_fn is not None and kind != FunctionKind.BUILTIN:
                lg.info(called_fn)
            elif called_fn is None and kind != FunctionKind.UNKNOWN:
                lg.error("called_fn not found at %s", pos)
