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
        return ".".join(self.components)


class Object:
    source_span: SourceSpan
    parent: Union["Object", None]
    children: dict[str, "Object"]
    name: str

    def __init__(
        self, source_span: SourceSpan, name: str, parent: "Object" = None
    ) -> None:
        self.source_span = source_span
        self.parent = parent
        self.name = name
        self.children = {}

    def full_path(self) -> ObjectPath:
        path = ObjectPath()
        obj = self
        while obj is not None:
            path.append_part(obj.name)
            obj = obj.parent
        return path

    def append_child(self, name: str, child: "Object") -> None:
        assert name not in self.children
        self.children[name] = child


class Module(Object):
    def __init__(
        self, source_span: SourceSpan, name: str, parent: "Object" = None
    ) -> None:
        super().__init__(source_span, name, parent)


class Class(Object):
    def __init__(
        self, source_span: SourceSpan, name: str, parent: "Object" = None
    ) -> None:
        super().__init__(source_span, name, parent)


class Function(Object):
    args: ast.arguments

    def __init__(
        self,
        args: ast.arguments,
        source_span: SourceSpan,
        name: str,
        parent: "Object" = None,
    ) -> None:
        super().__init__(source_span, name, parent)
        self.args = args


class ObjectCreator(ast.NodeVisitor):
    ob_stack: list[Object]
    filename: PurePath
    line_cnt: int

    def __init__(self, filename: PurePath, line_cnt: int):
        self.ob_stack = []
        self.filename = filename
        self.line_cnt = line_cnt

    def _parent(self) -> Union[Object, None]:
        if len(self.ob_stack) > 0:
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
        ss = SourceSpan(self.filename, 1, self.line_cnt)
        name = self._mod_name()

        ob = Module(ss, name, par)
        if par:
            par.append_child(name, ob)

        # Now visit children
        self.ob_stack.append(ob)
        self.generic_visit(mod)
        self.ob_stack.pop()

        return ob

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        par = self._parent()
        ss = self._source_span(node)
        name = node.name

        ob = Class(ss, name, par)
        if par:
            par.append_child(name, ob)

        # Now visit children
        self.ob_stack.append(ob)
        self.generic_visit(node)
        self.ob_stack.pop()

        return ob

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        par = self._parent()
        ss = self._source_span(node)
        name = node.name

        ob = Function(node.args, ss, name, par)
        if par:
            par.append_child(name, ob)

        # Now visit children
        self.ob_stack.append(ob)
        self.generic_visit(node)
        self.ob_stack.pop()

        return ob
