import ast
import pathlib
import pyhole.object as pho


default_filename = "simple/__init__.py"


def root_object(code: str, filename: str = default_filename) -> pho.Object:
    filepath = pathlib.PosixPath(filename)
    tree = ast.parse(code, str(filepath))
    lines = code.split('\n')
    line_cnt = len(lines)
    ctr = pho.ObjectCreator(filepath, line_cnt)
    return ctr.visit(tree)


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
    mod = root_object(code)

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
    mod = root_object(code)
    assert isinstance(mod, pho.Module)

    cls = mod.children['Thing']
    assert isinstance(cls, pho.Class)
    assert cls.name == "Thing"
