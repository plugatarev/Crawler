import contextlib
import glob
import os
from operator import itemgetter
from typing import List, Tuple

from loguru import logger

from src.model import ResultURL
from src.htmler import FancyHTMLer
from src.rankerer import PageRankerer


class Searcher:
    @staticmethod
    def search(query: str):
        ranker = PageRankerer()
        searcher = FancyHTMLer()

        htmls_number = 10

        with contextlib.suppress(FileExistsError):
            os.mkdir("search_results")

        file_names = glob.glob("search_results/" + "result_*")

        for name in file_names:
            os.remove(name)

        search_words = query.split(" ")
        if len(search_words) < 2:
            return
        # search_words = ["человек", "новосибирск"]
        distanced_urls = ranker.distance_score(search_words)

        if htmls_number > len(distanced_urls):
            htmls_number = len(distanced_urls)

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
            result_urls = ranker.get_normalized_page_ranks_by_result_urls(result_urls)

            # sort by total rating

            def total_rating_getter(url: ResultURL):
                return url.total_rating

            result_urls = sorted(result_urls, key=total_rating_getter, reverse=True)

            for i, url in enumerate(result_urls[:htmls_number], start=1):
                print(
                    f"URL ({url.url_id}): {url.url_name}, total score: {url.total_rating:.3f} (page_rank={url.page_rank_normalized_metric:.3f}, distance={url.distance_normalized_metric:.3f})"
                )
                words = ranker.db.get_words_by_url(url.url_id)
                searcher.create_marked_html_file(
                    f"result_{url.total_rating:.3f}_{url.page_rank_normalized_metric:.3f}_{url.distance_normalized_metric:.3f}_{url.url_id}_{url.url_name.removeprefix('http://').removeprefix('https://').split('/')[0].replace('?','')}.html",
                    words,
                    search_words,
                )
        else:
            logger.info("No URS found :(")
