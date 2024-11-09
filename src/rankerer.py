from typing import Dict

from loguru import logger

from src.database import DbActor
from src.model import PageRankURL


def calculate_ranks():
    PageRankerer().calculate_ranks()


class PageRankerer:
    def __init__(self) -> None:
        self.db = DbActor()
        self.iterations_count = 25
        self.rank_coeff = 0.85

    def close(self) -> None:
        self.db.close()

    def calculate_ranks(self):
        logger.info("Start calculating page ranks ...")
        url_ids = self.db.get_urls_ids()

        page_ranks: Dict[int, PageRankURL] = dict()

        for url_id in url_ids:
            links_count = self.db.get_from_url_count(
                url_id
            )  # на сколько страниц можно попасть с нашей
            references = self.db.get_from_urls_by_to(
                url_id
            )  # страницы которые смотрят на нашу
            page_ranks.setdefault(
                url_id,
                PageRankURL(
                    id=url_id,
                    links_count=links_count,
                    rank=1.0,
                    ratio=1.0 / links_count if links_count else 1.0,
                    references=references,
                ),
            )

        for _ in range(self.iterations_count):
            for page in page_ranks.values():
                other_links_sum = 0
                for ref in page.references:
                    other_links_sum += page_ranks.get(ref).ratio
                page.rank = (1 - self.rank_coeff) + self.rank_coeff * other_links_sum

            for page in page_ranks.values():
                page.ratio = (
                    page.rank / page.links_count if page.links_count else page.rank
                )

        self.db.fill_page_rank(list(page_ranks.values()))

        self.db.save_to_db_to_disk()

        logger.success(
            f"Page ranks are calculated over {self.iterations_count} iterations!"
        )
