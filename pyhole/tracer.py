import sys


class Tracer:
    start_tracing: bool

    def __init__(self):
        self.start_tracing = False
        self.old_trace_fn = None

    def enable_tracing(self):
        self.old_trace_fn = sys.gettrace()
        sys.settrace(self.trace_global)

    def disable_tracing(self):
        sys.settrace(self.old_trace_fn)
        self.old_trace_fn = None

    def _trace_line(self, frame):
        self.trace_line(frame)
        return self.trace_global

    # Override this
    def trace_line(self, frame):
        pass

    def _trace_call(self, frame):
        self.trace_call(frame)
        return self.trace_global

    # Override this
    def trace_call(self, frame):
        pass

    def _trace_return(self, frame):
        self.trace_return(frame)
        return self.trace_global

    # Override this
    def trace_return(self, frame):
        pass

    def trace_global(self, frame, event, _):
        if event == 'call':
            return self._trace_call(frame)
        if self.start_tracing and event == 'line':
            return self._trace_line(frame)
        if self.start_tracing and event == 'return':
            return self._trace_return(frame)
        return self.trace_global
