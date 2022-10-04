from pyhole.project import IncrementalProject
from pyhole.keyword import SimpleKeywordTracer
from pyhole.import_hook import populate_db
import codeop
import logging


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.DEBUG)

    project = IncrementalProject()
    tracer = SimpleKeywordTracer(project.db, project.kw_fns)

    code_str = """
import requests

def sample_func():
    requests.get("https://www.example.com/")

sample_func()
"""
    code = codeop.compile_command(code_str, "sample.py", 'exec')

    with populate_db(project):
        tracer.enable_tracing()
        exec(code)
