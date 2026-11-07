"""Deterministic source-reliability tiering.

A = primary / standards / official documentation / government / university
B = reputable reference & well-edited educational publishers
C = general tutorials, blogs, unknown sites (usable, but claims need corroboration)
D = user-generated Q&A / social / content farms (never used as sole support for a claim)

The LLM in QC1 adds a relevance judgement on top; this table makes the reliability part
transparent and reproducible instead of leaving it to the model's opinion.
"""
from __future__ import annotations

from urllib.parse import urlparse

TIER_A = {
    "rfc-editor.org", "datatracker.ietf.org", "ietf.org", "w3.org", "whatwg.org", "iso.org",
    "developer.mozilla.org", "docs.python.org", "python.org", "postgresql.org", "dev.mysql.com",
    "learn.microsoft.com", "docs.oracle.com", "docs.aws.amazon.com", "cloud.google.com",
    "developers.google.com", "web.dev", "nist.gov", "nih.gov", "who.int", "sqlite.org",
    "kernel.org", "docs.github.com", "nodejs.org", "react.dev", "ecma-international.org",
}
TIER_B = {
    "wikipedia.org", "britannica.com", "khanacademy.org", "ocw.mit.edu", "coursera.org",
    "edx.org", "cloudflare.com", "ibm.com", "redhat.com", "oreilly.com", "springer.com",
    "acm.org", "ieee.org", "nature.com", "sciencedirect.com", "arxiv.org", "freecodecamp.org",
    "digitalocean.com", "realpython.com", "httpwg.org", "mongodb.com", "atlassian.com",
    "books.google.com", "openlibrary.org", "postman.com", "restfulapi.net",
}
TIER_D = {
    "reddit.com", "quora.com", "stackexchange.com", "facebook.com", "x.com", "twitter.com",
    "pinterest.com", "tiktok.com", "brainly.com", "chegg.com", "scribd.com", "linkedin.com",
}
# stackoverflow is user generated but heavily moderated - treat as C, not D.


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def _match(host: str, pool: set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in pool)


def tier_for(url: str) -> str:
    host = domain_of(url)
    if not host:
        return "C"
    if host.endswith(".gov") or host.endswith(".edu") or ".gov." in host or ".ac." in host or host.endswith(".edu.in"):
        return "A"
    if _match(host, TIER_A):
        return "A"
    if _match(host, TIER_B):
        return "B"
    if _match(host, TIER_D):
        return "D"
    return "C"


TIER_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}
