"""도구 등록 트리거.

각 도메인의 tools 모듈을 import 하는 시점에 @mcp.tool() 데코레이터가 실행되어
단일 mcp 인스턴스에 등록된다. 새 도메인 추가 시 아래에 import 한 줄을 더한다.
(# noqa: F401 — import 자체가 부수효과)
"""
from src.core.mcp import mcp
from src.domains.sample import tools as sample_tools  # noqa: F401

__all__ = ["mcp"]
