from typing import List, Optional

from pydantic import BaseModel


class DailyForecast(BaseModel):
    date: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float


class WeatherResponse(BaseModel):
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float
    visibility: Optional[int] = None
    is_demo: bool = False


class ForecastResponse(BaseModel):
    city: str
    country: str
    forecasts: List[DailyForecast]
    is_demo: bool = False
