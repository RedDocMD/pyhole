import sys
import re
from types import FrameType


class Tracer:
    start_tracing: bool

    def __init__(self):
        self.old_trace_fn = None

    def enable_tracing(self):
        self.old_trace_fn = sys.gettrace()
        sys.settrace(self.trace_global)

    def disable_tracing(self):
        sys.settrace(self.old_trace_fn)
        self.old_trace_fn = None

    def _start_tracing(self) -> bool:
        return self.start_tracing

    def _trace_line(self, frame: FrameType):
        self.trace_line(frame)
        return self.trace_global

    # Override this
    def trace_line(self, frame: FrameType):
        pass

    def _trace_call(self, frame: FrameType):
        self.trace_call(frame)
        return self.trace_global

    # Override this
    def trace_call(self, frame: FrameType):
        pass

    def _trace_return(self, frame: FrameType):
        self.trace_return(frame)
        return self.trace_global

    # Override this
    def trace_return(self, frame: FrameType):
        pass

    def trace_global(self, frame: FrameType, event: str, _):
        if event == "call":
            return self._trace_call(frame)
        if event == "line":
            return self._trace_line(frame)
        if event == "return":
            return self._trace_return(frame)
        return self.trace_global


class PrintTracer(Tracer):
    """
    Tracer which simply prints a trace of the execution
    """

    print_line: bool
    ignore_patterns: list[re.Pattern]

    def __init__(self, print_line: bool = True, ignore_patterns: list[str] = []):
        super().__init__()
        self.print_line = print_line
        self.ignore_patterns = [re.compile(pat) for pat in ignore_patterns]

    def _should_ignore_filename(self, name):
        return any(map(lambda pat: pat.match(name), self.ignore_patterns))

    def trace_call(self, frame: FrameType):
        filename = frame.f_code.co_filename
        if self._should_ignore_filename(filename):
            return
        lineno = frame.f_lineno
        name = frame.f_code.co_name
        print("Called {} at {}:{}".format(name, filename, lineno))

    def trace_line(self, frame: FrameType):
        if self.print_line:
            filename = frame.f_code.co_filename
            if self._should_ignore_filename(filename):
                return
            lineno = frame.f_lineno
            name = frame.f_code.co_name
            print("Executed {} at {}:{}".format(name, filename, lineno))


class ExecTracer(Tracer):
    def __init__(self):
        super().__init__()

    def trace_call(self, frame: FrameType):
        if frame.f_code.co_filename != "sample.py":
            return
        print(frame)
        glob = frame.f_globals
        # glob = globals()
        # print("Globals:", glob)
        # print("global requests", "requests" in glob)
        print("Globals: ", glob.keys())
        # print(glob['root'] if 'root' in glob else None)
        # loc = locals()
        loc = frame.f_locals
        # print("Locals:", loc)
        # print("local requests", "requests" in loc)
        print("Locals: ", loc.keys())
