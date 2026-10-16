"""Pakiet po instalacji (`pip install .`) musi zawierać strony, które serwery wczytują z plików."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_package_data_lists_every_bundled_web_app():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = set(pyproject["tool"]["setuptools"]["package-data"]["bajka"])
    web_apps = {f"{page.parent.name}/*" for page in (ROOT / "bajka").glob("*_app/index.html")}

    assert web_apps == {"mobile_app/*", "panel_app/*"}
    assert web_apps <= declared
