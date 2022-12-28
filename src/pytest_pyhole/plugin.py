import pytest

from pyhole.tracer import Tracer
from pyhole.keyword import KeywordDb, CallTracer
from pyhole.project import Project
from pathlib import PurePath


tracer: Tracer | None = None
kwd_db = KeywordDb()


def pytest_addoption(parser):
    parser.addoption(
        "--project-root",
        nargs=1,
        type=PurePath,
        default=None,
    )


def pytest_sessionstart(session):
    global tracer, kwd_db
    root = session.config.getoption("--project-root")
    if root is not None:
        project = Project(root[0])
        tracer = CallTracer(project.db, project.kw_fns, kwd_db)


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call():
    global tracer
    if tracer is not None:
        tracer.enable_tracing()
    _ = yield
    if tracer is not None:
        tracer.disable_tracing()


def pytest_terminal_summary():
    global kwd_db
    if tracer is not None:
        kwd_db.print_fancy()
