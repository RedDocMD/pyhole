from pyhole.db import KeywordDb
from pyhole.project import Project
from pyhole.keyword import CallTracer
from pyhole.import_hook import populate_db
from pathlib import Path
import codeop
import logging


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.INFO)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"
    project = Project(root)
    # for thing in project.db:
    #     print(thing, project.db[thing])
    kwd_db = KeywordDb()
    tracer = CallTracer(project.db, project.kw_fns, kwd_db)
    code_str = """
import requests
def sample_func():
    requests.get("https://www.example.com/")
sample_func()
"""
    code = codeop.compile_command(code_str, "sample.py", 'exec')
    tracer.enable_tracing()
    exec(code)
    print(kwd_db)
