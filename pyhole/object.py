from pathlib import PurePath
from typing import Any, Union
from types import NoneType
import ast


class SourceSpan:
    filename: PurePath
    start_line: int
    end_line: int

    def __init__(self, filename: PurePath, start_line: int, end_line: int) -> None:
        self.filename = filename
        self.start_line = start_line
        self.end_line = end_line

    def __str__(self) -> str:
        return "{}:{}-{}".format(self.filename, self.start_line, self.end_line)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.filename == other.filename
                and self.start_line == other.start_line
                and self.end_line == other.end_line
            )
        raise NotImplementedError

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        raise NotImplementedError

    def __hash__(self):
        return hash((str(self.filename), self.start_line, self.end_line))


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
        assert name not in self.children, \
            f'{name} already child of {self.ob_type()} {self.name}'
        self.children[name] = child

    def ob_type(self) -> str:
        raise RuntimeError("ob_type must be subclassed!")

    def _dump_tree_intern(self, level=0) -> None:
        padding = "  " * level
        print(
            "{}{} ({}) => {}:{}".format(
                padding,
                self.name,
                self.ob_type(),
                self.source_span.filename,
                self.source_span.start_line,
            )
        )
        for child in self.children.values():
            child._dump_tree_intern(level + 1)

    def dump_tree(self) -> None:
        self._dump_tree_intern()

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.source_span == other.source_span and self.name == other.name
        return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return False

    def __hash__(self):
        return hash((self.source_span, self.ob_type(), self.name))


class Module(Object):
    def __init__(
        self, source_span: SourceSpan, name: str, parent: "Object" = None
    ) -> None:
        super().__init__(source_span, name, parent)

    def ob_type(self) -> str:
        return "mod"

    def __str__(self) -> str:
        return "mod {}".format(self.name)


class Class(Object):
    def __init__(
        self, source_span: SourceSpan, name: str, parent: "Object" = None
    ) -> None:
        super().__init__(source_span, name, parent)

    def ob_type(self) -> str:
        return "class"

    def __str__(self) -> str:
        return "class {}".format(self.name)


class Function(Object):
    args: ast.arguments

    def __init__(
        self,
        args: ast.arguments,
        source_span: SourceSpan,
        name: str,
        stmts,
        parent: "Object" = None,
    ) -> None:
        super().__init__(source_span, name, parent)
        self.args = args
        self.stmts = stmts

    def has_kwargs_dict(self) -> bool:
        return self.args.kwarg is not None

    def ob_type(self) -> str:
        return "func"

    def _format_args(self) -> str:
        def make_arg_list(args):
            return ", ".join(map(lambda x: x.arg, args))

        args = make_arg_list(self.args.args)
        posonly = make_arg_list(self.args.posonlyargs)
        kwonly = make_arg_list(self.args.kwonlyargs)

        out = ""
        if len(posonly) > 0:
            out += posonly
            out += "/"
        out += args
        if self.args.vararg:
            if (len(out) > 0 and out[-1] != "/") or len(out) > 0:
                out += ", "
            out += "*{}".format(self.args.vararg.arg)
            if len(kwonly) > 0:
                out += ", {}".format(kwonly)
        if self.args.kwarg:
            if (len(out) > 0 and out[-1] != "/") or len(out) > 0:
                out += ", "
            out += "**{}".format(self.args.kwarg.arg)

        return out

    def __str__(self) -> str:
        return "function {}({})".format(self.name, self._format_args())


def extract_statements_from_body(body):
    stmts = {}
    for stmt in body:
        stmts.update(extract_statements(stmt))
    return stmts


# TODO: Handle all valid nodes
def extract_statements(node):
    stmts = {node.lineno: node}
    match node:
        case ast.For(body=body):
            stmts.update(extract_statements_from_body(body))
        case ast.AsyncFor(body=body):
            stmts.update(extract_statements_from_body(body))
        case ast.While(body=body):
            stmts.update(extract_statements_from_body(body))
        case ast.If(body=body):
            stmts.update(extract_statements_from_body(body))
        case ast.With(body=body):
            stmts.update(extract_statements_from_body(body))
        case ast.AsyncWith(body=body):
            stmts.update(extract_statements_from_body(body))
    return stmts


class ObjectCreator(ast.NodeVisitor):
    ob_stack: list[Object]
    filename: PurePath
    line_cnt: int
    mod_name: str | NoneType

    def __init__(self, filename: PurePath, line_cnt: int, mod_name: str | NoneType = None):
        self.ob_stack = []
        self.filename = filename
        self.line_cnt = line_cnt
        self.mod_name = mod_name

    def _parent(self) -> Union[Object, None]:
        if len(self.ob_stack) > 0:
            return self.ob_stack[-1]
        else:
            return None

    def _source_span(self, node: ast.AST) -> SourceSpan:
        return SourceSpan(self.filename, node.lineno, node.end_lineno)

    def _mod_name(self) -> str:
        if self.mod_name:
            return self.mod_name
        parts = self.filename.parts
        if parts[-1] == "__init__.py":
            return parts[-2]
        else:
            return parts[-1].split('.')[0]

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

        stmts = extract_statements_from_body(node.body)
        ob = Function(node.args, ss, name, stmts, par)
        if par:
            par.append_child(name, ob)

        # Now visit children
        self.ob_stack.append(ob)
        self.generic_visit(node)
        self.ob_stack.pop()

        return ob
