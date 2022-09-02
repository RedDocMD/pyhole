from .tracer import Tracer
from .db import ObjectDb, Position
from .cache import FileCache
from .object import Function
import ast
from termcolor import colored


fun_txt = colored("Fun", 'grey', 'on_white')
stmt_txt = colored("Stmt", 'grey', 'on_yellow')
kwd_txt = colored("Valid keywords", 'grey', 'on_red', attrs=['bold'])


def get_position(frame):
    lineno = frame.f_lineno
    filename = frame.f_code.co_filename
    return Position(filename, lineno)


class FunctionNotFound(Exception):
    pass


def nearest_enclosing_function(pos, db):
    file_obs = []
    for ob_pos, ob in db.items():
        if ob_pos.filename == pos.filename:
            file_obs.append((ob_pos.start_line, ob))
    file_obs = sorted(file_obs, key=lambda x: x[0], reverse=True)
    idx = 0
    while idx < len(file_obs):
        lineno, ob = file_obs[idx]
        if lineno > pos.start_line:
            idx += 1
        elif isinstance(ob, Function):
            return ob
    return None


def expr_has_call_expression(expr):
    match expr:
        case ast.Call():
            return expr
        case _:
            return None


def stmt_has_call_expression(stmt):
    match stmt:
        case ast.Return(value=expr):
            return expr_has_call_expression(expr)
        case ast.Assign(value=expr):
            return expr_has_call_expression(expr)
        case ast.AugAssign(value=expr):
            return expr_has_call_expression(expr)
        case _:
            return None


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
        self.doing_call = False
        self.call_kwds = []

    def trace_call(self, frame):
        pos = get_position(frame)
        self.call_stack.append(pos)
        if pos in self.db:
            ob = self.db[pos]
            self.aux_call_stack.append((pos, ob))
            if ob in self.kw_fns:
                print(fun_txt, ob, ob.source_span)
                kwds = extract_keywords(self.call_kwds)
                if len(kwds) > 0:
                    print(kwd_txt, ', '.join(kwds))
                self.kwfn_stack.append(ob)
        if self.doing_call:
            self.doing_call = False

    def trace_line(self, frame):
        if len(self.kwfn_stack) == 0:
            return
        if self.doing_call:
            return
        kw_ob = self.kwfn_stack[-1]
        call_ob, _ = self.aux_call_stack[-1]
        if kw_ob != call_ob:
            return
        # pos = get_position(frame)
        # line = self.fc[pos]
        # line = line.strip()
        # print("Line", line)
        # try:
        #     stmt = ast.parse(line, pos.filename, mode="single")
        #     print("Stmt", ast.dump(stmt))
        # except Exception as e:
        #     print("Exception", e)
        # print(kw_ob.source_span.filename, frame.f_code.co_filename)
        # if str(kw_ob.source_span.filename) != str(frame.f_code.co_filename):
        #     return
        pos = get_position(frame)
        enc_ob = nearest_enclosing_function(pos, self.db)
        if enc_ob is None or enc_ob != kw_ob:
            return
        stmt = kw_ob.stmts[frame.f_lineno]
        # print(stmt_txt, ast.dump(stmt))
        call_expr = stmt_has_call_expression(stmt)
        if call_expr:
            self.doing_call = True
            self.call_kwds = call_expr.keywords

    def trace_return(self, frame):
        call_pos = self.call_stack[-1]
        self.call_stack.pop()
        if len(self.aux_call_stack) > 0:
            call_ob, pos = self.aux_call_stack[-1]
            if pos == call_pos:
                self.aux_call_stack.pop()
                if len(self.kwfn_stack) != 0 and self.kwfn_stack[-1] == call_ob:
                    self.kwfn_stack.pop()
