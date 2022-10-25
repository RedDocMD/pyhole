from pyhole.db import KeywordDb
from pyhole.project import Project
from pyhole.keyword import CallTracer
from pyhole.import_hook import populate_db
from pyhole.tracer import Tracer
from pathlib import Path
import codeop
import logging


def trace_fn(tracer: Tracer, code: str) -> None:
    code_ob = codeop.compile_command(code, "sample.py", "exec")
    tracer.enable_tracing()
    exec(code_ob, globals())
    tracer.disable_tracing()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"
    project = Project(root)
    kwd_db = KeywordDb()
    tracer = CallTracer(project.db, project.kw_fns, kwd_db)

    get_code_str = """
import requests
def sample_func():
    requests.get("https://www.example.com/")
sample_func()
"""

    post_code_str = """
import requests
def sample_func():
    requests.post("https://www.example.com/")
sample_func()
"""

    trace_fn(tracer, get_code_str)
    trace_fn(tracer, post_code_str)

    print(kwd_db)
