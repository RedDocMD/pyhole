from pyhole import test_case, exec_cases, add_project, get_kwd_db
from pyhole.project import Project
from pathlib import Path
import logging
import requests


@test_case
def test_get():
    requests.get("https://httpbin.org/get")


@test_case
def test_post():
    requests.post("https://httpbin.org/post", data={'key': 'value'})


@test_case
def test_session():
    sess = requests.Session()
    sess.headers.update({'x-test': 'true'})
    sess.get("https://httpbin.org/get")
    sess.post("https://httpbin.org/post")
    sess.patch("https://httpbin.org/patch")
    sess.delete("https://httpbin.org/delete")
    sess.put("https://httpbin.org/put")


@test_case
def test_json():
    resp = requests.get("https://httpbin.org/json")
    resp.json()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"

    project = Project(root)
    for fn in project.kw_fns.values():
        print(fn)
    add_project(project)
    exec_cases()
    kwd_db = get_kwd_db()
    print('#### POSSIBLE KEYWORDS ####')
    for fn, kwds in kwd_db.items():
        print(f'{fn}: {kwds}')
