from src.core.mcp import mcp
from src.users import prompts as db_prompts  # noqa: F401
from src.users import resources as db_resources  # noqa: F401
from src.users import tools as db_tools  # noqa: F401
from src.news import prompts as news_prompts  # noqa: F401
from src.news import resources as news_resources  # noqa: F401
from src.news import tools as news_tools  # noqa: F401
from src.utils import tools as utils_tools  # noqa: F401
from src.sample.basic import tools as basic_tools  # noqa: F401
from src.weather import prompts as weather_prompts  # noqa: F401
from src.weather import resources as weather_resources  # noqa: F401
from src.weather import tools as weather_tools  # noqa: F401

__all__ = ["mcp"]
