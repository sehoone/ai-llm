from abc import ABC, abstractmethod

from fastmcp import FastMCP

from src.core.logging import get_logger


class BaseMCPServer(ABC):
    def __init__(self, name: str) -> None:
        self.mcp = FastMCP(name)
        self.logger = get_logger(name)
        self._register_tools()

    @abstractmethod
    def _register_tools(self) -> None: ...

    def run(self) -> None:
        self.logger.info(f"Starting {self.mcp.name}...")
        self.mcp.run()
