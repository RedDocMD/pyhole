from .tracer import Tracer
from .db import ObjectDb, Position
from .cache import FileCache
from .object import Function
import ast
from termcolor import colored
from logging import debug


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
        self.call_stack = []
        self.aux_call_stack = []
        self.kwfn_stack = []
        # Call_exprs must be sorted in terms of call order
        self.call_exprs = []
        self.doing_call = False

    def trace_call(self, frame):
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
        if self.doing_call:
            self.doing_call = False

    def _update_call_expressions(self, stmt):
        call_exprs = stmt_call_expressions(stmt)
        if call_exprs:
            self.doing_call = True
            self.call_exprs.extend(call_exprs)

    def trace_line(self, frame):
        if self.doing_call:
            return
        if not self.aux_call_stack:
            return
        call_pos, call_ob = self.aux_call_stack[-1]
        if not isinstance(call_ob, Function):
            return
        debug('%s: %s', call_ob, call_pos)
        pos = get_position(frame)
        enc_ob = nearest_enclosing_function(pos, self.db)
        if not enc_ob or enc_ob != call_ob:
            return
        debug(call_ob.stmts)
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

    def trace_return(self, frame):
        call_pos = self.call_stack[-1]
        self.call_stack.pop()
        if len(self.aux_call_stack) > 0:
            call_ob, pos = self.aux_call_stack[-1]
            if pos == call_pos:
                self.aux_call_stack.pop()
                if len(self.kwfn_stack) != 0 and self.kwfn_stack[-1] == call_ob:
                    self.kwfn_stack.pop()
