from pyhole.tracer import PrintTracer
import codeop
import logging


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.DEBUG)

    tracer = PrintTracer(print_line=False, ignore_patterns=[r"<frozen.*"])

    code_str = """
import requests

def sample_func():
    requests.get("https://www.example.com/")
"""
    code = codeop.compile_command(code_str, "sample.py", 'exec')

    tracer.enable_tracing()
    exec(code)
