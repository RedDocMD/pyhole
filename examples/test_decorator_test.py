from pyhole import test_case, exec_cases, add_project, get_kwd_db
from pyhole.project import Project
from pathlib import Path
import logging
import requests


@test_case
def test_get():
    requests.get("https://www.example.com/")


@test_case
def test_post():
    requests.post("https://www.example.com/")


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"

    add_project(Project(root))
    exec_cases()
    print(get_kwd_db())
