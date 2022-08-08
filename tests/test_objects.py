import ast
import pathlib
import pyhole.object as pho


def test_module():
    code = """
def standalone_func1():
    pass

def standalone_func2(arg):
    pass

def standalone_func3(**args):
    pass


class Thing:
    def __init__(self):
        pass

    def member1(self):
        pass
"""
    filename = pathlib.PosixPath("simple/__init__.py")
    tree = ast.parse(code, str(filename))
    lines = code.split('\n')
    line_cnt = len(lines)

    ctr = pho.ObjectCreator(filename, line_cnt)
    mod = ctr.visit(tree)

    assert isinstance(mod, pho.Module)
    assert mod.name == "simple"


def test_class():
    code = """
class Thing:
    def __init__(self):
        pass

    def member1(self):
        pass
"""
    filename = pathlib.PosixPath("simple/__init__.py")
    tree = ast.parse(code, str(filename))
    lines = code.split('\n')
    line_cnt = len(lines)

    ctr = pho.ObjectCreator(filename, line_cnt)
    mod = ctr.visit(tree)

    assert isinstance(mod, pho.Module)

    cls = mod.children['Thing']

    assert isinstance(cls, pho.Class)
    assert cls.name == "Thing"
