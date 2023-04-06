from pyhole import test_case, exec_cases, add_project, get_kwd_db, utils
from pyhole.db import KeywordDb
from pyhole.project import Project
from pathlib import Path
from io import StringIO
import logging
import requests


TEST_URL = "http://localhost:8080"


@test_case
def test_get():
    requests.get("{}/get".format(TEST_URL))


@test_case
def test_post():
    requests.post("{}/post".format(TEST_URL), data={'key': 'value'})


@test_case
def test_session():
    sess = requests.Session()
    sess.headers.update({'x-test': 'true'})
    sess.get("{}/get".format(TEST_URL))
    sess.post("{}/post".format(TEST_URL))
    sess.patch("{}/patch".format(TEST_URL))
    sess.delete("{}/delete".format(TEST_URL))
    sess.put("{}/put".format(TEST_URL))


@test_case
def test_json():
    resp = requests.get(f"{TEST_URL}/json")
    resp.json()


def print_simple(kdb: KeywordDb) -> None:
    for k, v in kdb.items():
        print(k, ":", v)


def main():
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"

    project = Project(root)
    # for fn in project.kw_fns.values():
    #     print(fn)
    add_project(project)
    exec_cases()
    kwd_db = get_kwd_db()
    print(utils.boxed('Found'))
    kwd_db.print_fancy()
    cnt = 0
    print(utils.boxed('Not Found'))
    for fn in project.kw_fns.values():
        if fn not in kwd_db.db:
            print(fn)
            cnt += 1
    print('Not found count:', cnt)
    with StringIO() as f:
        kwd_db.render_rst(f)
        print('Rendered RST:')
        print(f.getvalue())


if __name__ == "__main__":
    main()
