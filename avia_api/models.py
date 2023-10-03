from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Ticket:
    price: float
    origin_name: str
    origin_code: str
    destination_name: str
    destination_code: str
    link: str
    departure_at: datetime

@dataclass(frozen=True, kw_only=True)
class Direction:
    id_direction: int
    origin: str
    destination: str
    max_price: int
    count_posts: int