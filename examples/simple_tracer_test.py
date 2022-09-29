from pyhole.project import Project
from pyhole.keyword import SimpleKeywordTracer
from pyhole.import_hook import populate_db
from pathlib import Path
import codeop
import logging


if __name__ == "__main__":
    with populate_db():
        logging.basicConfig(format='%(levelname)s: %(message)s',
                            level=logging.DEBUG)
        cwd = Path.cwd()
        # Run from project root
        root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"
        project = Project(root)
        # for thing in project.db:
        #     print(thing, project.db[thing])
        tracer = SimpleKeywordTracer(project.db, project.kw_fns)
        code_str = """
import requests

def sample_func():
    requests.get("https://www.example.com/")

sample_func()
"""
        code = codeop.compile_command(code_str, "sample.py", 'exec')
        tracer.enable_tracing()
        exec(code)
