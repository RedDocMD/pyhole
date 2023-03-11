import enum


class Indexer(enum.Enum):
    RUST = 0
    PYTHON = 1


indexer = Indexer.RUST

if indexer == Indexer.RUST:
    from parse_py import (SourceSpan, ObjectPath, Object, AltObject, Module,
                          Function, Class, FormalParam, FormalParamKind)
    from parse_py import module_from_dir
    from .test_decorator import test_case, add_project, exec_cases, get_kwd_db
else:
    from .object import (SourceSpan, ObjectPath, Object, AltObject, Module,
                         Function, Class, FormalParam, FormalParamKind)
    from .test_decorator import test_case, add_project, exec_cases, get_kwd_db
