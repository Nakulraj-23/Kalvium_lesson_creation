import types

import pytest

from lesson_tool.config import Settings
from lesson_tool.fake_llm import FakeLLM
from lesson_tool.research import providers as real
from lesson_tool.storage import Store

PAGE = """HTTP defines a set of request methods.

The GET method requests a representation of the specified resource. Requests using GET should only retrieve data and are safe.

The POST method submits an entity to the specified resource, often causing a change in state on the server.

Successful responses (200-299). Client error responses (400-499). Server error responses (500-599)."""


def make_providers(fail_all_text=False):
    def search_web(q, max_results=6):
        if fail_all_text:
            raise ConnectionError("offline")
        return [
            {"title": "HTTP request methods - MDN", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods", "snippet": "GET POST"},
            {"title": "Some blog", "url": "https://someblog.dev/http", "snippet": "http blog"},
            {"title": "reddit thread", "url": "https://www.reddit.com/r/webdev/x", "snippet": "lol"},
        ]

    def search_wikipedia(q, limit=2, timeout=15):
        if fail_all_text:
            raise ConnectionError("offline")
        return [{"title": "HTTP - Wikipedia", "url": "https://en.wikipedia.org/wiki/HTTP", "text": PAGE}]

    return types.SimpleNamespace(
        keywords_from=real.keywords_from,
        relevant_excerpt=real.relevant_excerpt,
        fetch_page_text=lambda url, timeout=15: "" if "someblog" in url else PAGE,
        search_web=search_web,
        search_wikipedia=search_wikipedia,
        resolve_redirect=lambda u: u,
        search_books=lambda q, max_results=5, api_key="", timeout=15: [
            {"title": "HTTP: The Definitive Guide", "authors": ["David Gourley", "Brian Totty"], "year": "2002",
             "url": "https://books.google.com/books?id=x", "description": "Comprehensive guide to HTTP."}],
        search_youtube=lambda q, max_results=6, api_key="", timeout=15: [
            {"id": "abc123", "title": "HTTP Crash Course", "channel": "Traversy Media", "duration_sec": 600, "views": 1, "url": "https://www.youtube.com/watch?v=abc123"},
            {"id": "long1", "title": "10 hour lecture", "channel": "x", "duration_sec": 36000, "views": 1, "url": "https://www.youtube.com/watch?v=long1"}],
    )


@pytest.fixture(autouse=True)
def reset_fake():
    FakeLLM.fail_tasks = set()
    yield
    FakeLLM.fail_tasks = set()


@pytest.fixture
def settings(tmp_path):
    s = Settings()
    s.llm_backend = "fake"
    s.data_dir = tmp_path
    s.use_grounded_search = True
    return s


@pytest.fixture
def store(settings):
    return Store(settings.data_dir)


@pytest.fixture
def providers():
    return make_providers()


@pytest.fixture
def links_ok():
    return lambda urls: {u: True for u in urls}
