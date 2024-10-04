from dataclasses import dataclass


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
