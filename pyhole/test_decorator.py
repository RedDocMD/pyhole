from types import CodeType, FunctionType, NoneType
from typing import Any
from pyhole.db import KeywordDb
from pyhole.keyword import CallTracer
from pyhole.project import Project
from pyhole.tracer import Tracer

projects: list[Project] = []
kwd_db = KeywordDb()
tracer: Tracer | None = None


class TestCase:
    code: CodeType
    fn_globals: dict[str, Any]

    def __init__(self, code: CodeType, fn_globals: dict[str, Any]) -> None:
        self.code = code
        self.fn_globals = fn_globals

    def exec(self) -> None:
        global tracer

        tracer.enable_tracing()
        exec(self.code, self.fn_globals)
        tracer.disable_tracing()


test_cases: list[TestCase] = []


def test_case(fn: FunctionType) -> None:
    global test_cases

    case = TestCase(fn.__code__, fn.__globals__)
    test_cases.append(case)


def exec_cases() -> None:
    global tracer, test_cases, projects, kwd_db

    if not tracer:
        dbs = list(map(lambda x: x.db, projects))
        kw_fns = list(map(lambda x: x.kw_fns, projects))
        tracer = CallTracer(dbs, kw_fns, kwd_db)
    for case in test_cases:
        case.exec()


def add_project(project: Project) -> None:
    global projects

    projects.append(project)


def get_kwd_db() -> KeywordDb:
    global kwd_db

    return kwd_db
