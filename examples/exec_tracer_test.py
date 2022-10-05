from pyhole.tracer import ExecTracer
import codeop
import logging


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.DEBUG)

    tracer = ExecTracer()

    code_str = """
import requests

def f1(a, b):
    c = a * b
    return c / 3

def f2(a):
    p = a ** 3
    return f1(a, p)

def f3():
    a = 4 * 6 - 7
    return f2(a)

f3()
"""
    code = codeop.compile_command(code_str, "sample.py", 'exec')

    tracer.enable_tracing()
    exec(code)
