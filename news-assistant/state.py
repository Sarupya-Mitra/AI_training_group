from typing import TypedDict


class NewsState(TypedDict, total=False):
    topic: str
    findings: str
    sources: list[str]
    summary: str
    email: str
    error: str
