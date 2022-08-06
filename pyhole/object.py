from pathlib import PurePath


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
    parent: 'Object'
    name: str

    def __init__(self, source_span: SourceSpan, name: str, parent: 'Object' = None) -> None:
        self.source_span = source_span
        self.parent = parent
        self.name = name

    def full_path(self) -> ObjectPath:
        path = ObjectPath()
        obj = self
        while obj is not None:
            path.append_part(obj.name)
            obj = obj.parent
        return path


class Module(Object):
    pass


class Class(Object):
    pass


class Function(Object):
    pass
