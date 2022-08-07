from pathlib import PurePath
from typing import Any, Union
import ast


class SourceSpan:
    filename: PurePath
    start_line: int
    end_line: int

    def __init__(self, filename: PurePath, start_line: int, end_line: int) -> None:
        self.filename = filename
        self.start_line = start_line
        self.end_line = end_line


class ObjectPath:
    components: list[str]

    def __init__(self, components=None) -> None:
        if components is None:
            components = []
        self.components = components

    def append_part(self, part: str) -> None:
        self.components.append(part)

    def __str__(self) -> str:
        return '.'.join(self.components)


class Object:
    source_span: SourceSpan
    parent: Union['Object', None]
    children: list['Object']
    name: str

    def __init__(self, source_span: SourceSpan, name: str, parent: 'Object' = None) -> None:
        self.source_span = source_span
        self.parent = parent
        self.name = name
        self.children = []

    def full_path(self) -> ObjectPath:
        path = ObjectPath()
        obj = self
        while obj is not None:
            path.append_part(obj.name)
            obj = obj.parent
        return path

    def append_child(self, child: 'Object') -> None:
        self.children.append(child)


class Module(Object):
    def __init__(self, source_span: SourceSpan, name: str, parent: 'Object' = None) -> None:
        super().__init__(source_span, name, parent)


class Class(Object):
    pass


class Function(Object):
    pass


class ObjectCreator(ast.NodeVisitor):
    ob_stack: list[Object]
    filename: PurePath

    def __init__(self, filename: PurePath):
        self.ob_stack = []
        self.filename = filename

    def _parent(self) -> Union[Object, None]:
        if len(self.ob_stack) == 0:
            return self.ob_stack[-1]
        else:
            return None

    def _source_span(self, node: ast.AST) -> SourceSpan:
        return SourceSpan(self.filename, node.lineno, node.end_lineno)

    def _mod_name(self) -> str:
        parts = self.filename.parts
        if parts[-1] == "__init__.py":
            return parts[-2]
        else:
            return parts[-1]

    def visit_Module(self, mod: ast.Module) -> Any:
        par = self._parent()
        ss = self._source_span(mod)
        name = self._mod_name()
        ob = Module(ss, name, par)
        # Now visit children
        self.ob_stack.append(ob)
        self.generic_visit(mod)
        self.ob_stack.pop()