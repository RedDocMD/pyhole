from .tracer import Tracer
from .db import ObjectDb, Position
from .cache import FileCache
import ast


def get_position(frame):
    lineno = frame.f_lineno
    filename = frame.f_code.co_filename
    return Position(filename, lineno)


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

    def trace_call(self, frame):
        pos = get_position(frame)
        self.call_stack.append(pos)
        if pos in self.db:
            ob = self.db[pos]
            self.aux_call_stack.append((pos, ob))
            if ob in self.kw_fns:
                print(ob)
                self.kwfn_stack.append(ob)

    def trace_line(self, frame):
        if len(self.kwfn_stack) == 0:
            return
        kw_ob = self.kwfn_stack[-1]
        call_ob, _ = self.aux_call_stack[-1]
        if kw_ob != call_ob:
            return
        pos = get_position(frame)
        line = self.fc[pos]
        stmt = ast.parse(line, pos.filename, mode="eval")
        print(ast.dump(stmt))

    def trace_return(self, frame):
        call_pos = self.call_stack[-1]
        self.call_stack.pop()
        if len(self.aux_call_stack) > 0:
            call_ob, pos = self.aux_call_stack[-1]
            if pos == call_pos:
                self.aux_call_stack.pop()
                if len(self.kwfn_stack) != 0 and self.kwfn_stack[-1] == call_ob:
                    self.kwfn_stack.pop()
