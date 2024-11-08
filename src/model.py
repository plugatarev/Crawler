from dataclasses import dataclass
from typing import List


@dataclass
class Element:
    word: str
    location: int = 0
    word_id: int = 0
    href: str = ""
    link_id: int = 0


@dataclass
class LinkToGo:
    link: str
    depth: int = 0

    def __hash__(self) -> int:
        return hash(self.link)


@dataclass
class FetchedUrl:
    url: str
    text: str
    depth: int = 0

@dataclass
class WordLocationsCombination:
    url: int
    word_locations: List[int]


@dataclass
class PageRankURL:
    id: int
    links_count: int
    rank: float
    ratio: float
    references: List[int]


@dataclass
class ResultURL:
    url_id: int = 0
    url_name: str = ""
    distance_normalized_metric: float = 0.0
    distance_raw_metric: float = 0.0
    page_rank_normalized_metric: float = 0.0
    page_rank_raw_metric: float = 0.0
    total_rating: float = 0.0
