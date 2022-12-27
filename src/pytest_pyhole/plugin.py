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


def pytest_sessionfinish():
    global kwd_db, tracer
    print("\nDB:")
    for k, v in kwd_db.items():
        print(k, ":", v)
    tracer = None


def pytest_runtest_setup():
    global tracer
    if tracer is not None:
        tracer.enable_tracing()


def pytest_runtest_teardown():
    global tracer
    if tracer is not None:
        tracer.disable_tracing()
