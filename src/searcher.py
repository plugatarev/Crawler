import contextlib
import glob
import os
from operator import itemgetter
from typing import List, Tuple

from loguru import logger

from src.model import ResultURL
from src.htmler import Htmler
from src.database import DbActor

from src.model import ResultURL, WordLocationsCombination


class Searcher:
    def __init__(self) -> None:
        self.db = DbActor()

    def close(self) -> None:
        self.db.close()

    def search(self, query: str):
        htmler = Htmler()

        output_htmls_number = 10

        with contextlib.suppress(FileExistsError):
            os.mkdir("search_results")

        file_names = glob.glob("search_results/" + "result_*")

        for name in file_names:
            os.remove(name)

        search_words = [search_word.lower() for search_word in query.split(" ")]

        if len(search_words) < 2:
            return

        distanced_urls = self.distance_score(search_words)

        if output_htmls_number > len(distanced_urls):
            output_htmls_number = len(distanced_urls)

        if len(distanced_urls) > 0:
            # [url_id, distance_rank]
            distanced_urls: List[Tuple[int, float]] = sorted(
                distanced_urls, key=itemgetter(1), reverse=True
            )

            result_urls = [
                ResultURL(
                    url_id=element[0],
                    distance_normalized_metric=element[1],
                )
                for element in distanced_urls
            ]
            logger.debug(len(result_urls))
            result_urls = self.get_normalized_page_ranks_by_result_urls(result_urls)

            # sort by total rating

            def total_rating_getter(url: ResultURL):
                return url.total_rating

            result_urls = sorted(result_urls, key=total_rating_getter, reverse=True)

            for _, url in enumerate(result_urls[:output_htmls_number], start=1):
                print(
                    f"URL ({url.url_id}): {url.url_name}, total score: {url.total_rating:.3f} (page_rank={url.page_rank_normalized_metric:.3f}, distance={url.distance_normalized_metric:.3f})"
                )
                words = self.db.get_words_by_url(url.url_id)
                htmler.create_marked_html_file(
                    f"result_{url.total_rating:.3f}_{url.page_rank_normalized_metric:.3f}_{url.distance_normalized_metric:.3f}_{url.url_id}_{url.url_name.removeprefix('http://').removeprefix('https://').split('/')[0].replace('?','')}.html",
                    words,
                    search_words,
                )
        else:
            logger.info("No URS found :(")

    def distance_score(self, words):
        combinations: List[WordLocationsCombination] = self.db.get_words_location_combinations(words)

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

        # a10 b20 ccccccc a30 cccc a

        for i in min_distance_list:
            for j in combinations:
                if j.url == i[0]:
                    local_distance = 0
                    for k in range(len(j.word_locations) - 1):
                        diff = abs(j.word_locations[k] - j.word_locations[k - 1])
                        local_distance += diff
                if i[1] > local_distance:
                    i[1] = local_distance

        return self.normalized_score(min_distance_list, True)

    def normalized_score(self, distance_list, is_small_better):
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
