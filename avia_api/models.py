from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Ticket:
    price: float
    origin_name: str
    destination_name: str
    link: str
    departure_at: datetime | str
    last_update: str | None

@dataclass(frozen=True, kw_only=True)
class Direction:
    id_direction: int
    origin: str
    destination: str
    max_price: int
    count_posts: int

@dataclass(frozen=True, kw_only=True)
class PriceSettings:
    difference: int
    critical_difference: int
