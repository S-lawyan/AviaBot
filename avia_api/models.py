from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Ticket:
    price: float
    origin_name: str
    destination_name: str
    destination_code: str
    link: str
    departure_at: datetime | str
    last_update: str | None

@dataclass(frozen=True, kw_only=True)
class Direction:
    id_direction: int
    direction_from: str
    direction_to: str
    origin_code: str
    destination_code: str
    max_price: int
    count_posts: int
    sent_posts: int

@dataclass(frozen=True, kw_only=True)
class PriceSettings:
    difference: int
    critical_difference: int
