import time
from typing import Dict, List

from loguru import logger

from src.database import DbActor
from src.model import PageRankURL, ResultURL, WordLocationsCombination


class PageRankerer:
    def __init__(self) -> None:
        self.db = DbActor()
        self.iterations_count = 25
        self.rank_coeff = 0.85

    def close(self) -> None:
        self.db.close()

    def distance_score(self, words):
        combinations: List[
            WordLocationsCombination
        ] = self.db.get_words_location_combinations(words)
        if len(combinations) == 0:
            return []

        unique_ids = set()
        min_distance_list = []

        if len(combinations[0].word_locations) == 1:
            for i in min_distance_list:
                min_distance_list[i][1] = 1.0
        else:
            for i in combinations:
                if i.url not in unique_ids:
                    min_distance_list.append([i.url, 999999.9])
                    unique_ids.add(i.url)

        for i in min_distance_list:
            for j in combinations:
                if j.url == i[0]:
                    local_distance = 0
                    for k in range(len(j.word_locations) - 1):
                        diff = abs(j.word_locations[k] - j.word_locations[k - 1])
                        local_distance += diff
                if i[1] > local_distance:
                    i[1] = local_distance

        return self.normalized_score(min_distance_list)

    def normalized_score(self, distance_list, is_small_better=True):
        columns = list(zip(*distance_list))

        min_score = min(columns[1])
        max_score = max(columns[1])

        if is_small_better:
            for i in distance_list:
                i[1] = float(min_score) / i[1]
        else:
            for i in distance_list:
                i[1] = float(i[1]) / max_score

        return distance_list

    def calculate_ranks(self):
        logger.info("Start calculating page ranks ...")
        start_time = time.perf_counter()
        url_ids = self.db.get_unique_urls_ids()

        page_ranks: Dict[int, PageRankURL] = dict()

        for url_id in url_ids:
            links_count = self.db.get_from_url_count(url_id)
            references = self.db.get_from_urls_by_to(url_id)
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

        for i in range(self.iterations_count):
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
            f"Page ranks are calculated over {self.iterations_count} iterations! "
            f"It took {time.perf_counter() - start_time:.2f} seconds."
        )

    def get_normalized_page_ranks_by_result_urls(
        self, urls: List[ResultURL]
    ) -> List[ResultURL]:
        if self.db.db.execute("SELECT COUNT(*) FROM page_rank").fetchone()[0] == 0:
            raise Exception("Empty ranks table")

        urls_dict = {url.url_id: url for url in urls}

        urls_with_page_rank = self.db.get_urls_with_page_ranks(
            [url.url_id for url in urls]
        )

        assert len(urls_with_page_rank) > 0

        max_rank = max([url.page_rank_raw_metric for url in urls_with_page_rank])

        # normalize
        ratio = 1 / max_rank
        for url in urls_with_page_rank:
            url.page_rank_normalized_metric = url.page_rank_raw_metric * ratio

        # modify and calc summary
        for url in urls_with_page_rank:
            url.distance_normalized_metric = urls_dict[
                url.url_id
            ].distance_normalized_metric
            url.total_rating = (
                url.page_rank_normalized_metric + url.distance_normalized_metric
            ) / 2

        return urls_with_page_rank


def calculate_ranks():
    PageRankerer().calculate_ranks()
