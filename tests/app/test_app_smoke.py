import pytest

pytest.importorskip("streamlit")
pytest.importorskip("chromadb")

from streamlit.testing.v1 import AppTest


def test_app_boots_without_exceptions():
    at = AppTest.from_file("app.py", default_timeout=300)
    at.run()
    assert not at.exception
