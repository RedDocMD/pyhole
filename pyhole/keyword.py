from typing import Any
from .tracer import Tracer
from .db import ObjectDb, Position
from .cache import FileCache
from .object import Function
import ast
from termcolor import colored
import logging as lg
from types import FrameType


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


def name_from_expr(expr):
    if isinstance(expr, str):
        return expr
    elif isinstance(expr, ast.Constant):
        return name_from_expr(expr.value)
    elif isinstance(expr, ast.Name):
        return name_from_expr(expr.id)
    else:
        return lg.error("Unknown expr %s to find name", expr)


def find_called_fn(expr: ast.Expression, loc: dict[str, Any], glob: dict[str, Any]):
    match expr:
        case ast.Name(id=idv):
            # TODO: Check the expr_context
            name = name_from_expr(idv)
            if name in loc:
                return loc[name]
            elif name in glob:
                return glob[name]
            else:
                lg.error("%s for Name not found in loc or glob", name)
        case ast.Attribute(value=value, attr=attr):
            name = name_from_expr(value)
            if name in loc:
                base = loc[name]
            elif name in glob:
                base = glob[name]
            else:
                lg.error("%s for Attribute not found in loc or glob", name)
                return None
            lg.debug("Base: %s", base)
            pass
    # lg.debug(expr)
    return None


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
        loc = frame.f_locals
        glob = frame.f_globals
        for call_expr in call_exprs:
            called_fn = find_called_fn(call_expr.func, loc, glob)
            if called_fn:
                lg.debug(called_fn)
            else:
                lg.debug("called_fn not found")
