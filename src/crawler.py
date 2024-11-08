import asyncio
import contextlib
import csv
import datetime
import os
import re
import threading
import time
from typing import List

import aiohttp
import bs4
from bs4 import BeautifulSoup, Comment
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from src.database import DbActor
from src.model import Element, FetchedUrl, LinkToGo
from src.settings import STATISTICS_FILENAME, DATABASE_FILENAME


def start_crawler():
    with contextlib.suppress(FileNotFoundError):
        os.remove(DATABASE_FILENAME)
        os.remove(STATISTICS_FILENAME)

    Crawler().start_crawl()


class Crawler:
    START_URL_LIST = [LinkToGo("https://ngs.ru/"), LinkToGo("https://lenta.ru/")]
    MAX_DEPTH = 2
    FETCH_EXCEPTION_SLEEP_INTERVAL = 0.25
    FETCH_MAX_RETRIES_COUNT = 3
    FETCH_BATCH_SIZE = 30
    FETCH_TOTAL_TIMEOUT = 10
    FETCH_CONNECT_TIMEOUT = 2
    IDLE_WORK_SLEEP_INTERVAL = 5
    IDLE_COUNT_BEFORE_EXIT = 3
    STAT_INTERVAL = 2

    def __init__(self, url_list=START_URL_LIST, depth=MAX_DEPTH) -> None:
        for url in url_list:
            url.link = url.link.strip("/")
        self.start_url_list = url_list[:]
        self.urls_to_crawl = url_list[:]
        self.crawled_urls = []
        self.depth = depth
        self.db = DbActor()
        self.crawl_count = 0
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.error_processed_urls = []
        self.pages_to_process: List[FetchedUrl] = []
        self.stop_flag = False
        self.parser = Parser()

    def start_crawl(self):
        logger.info(f"Starting web crawler ... urls_to_crawl={self.urls_to_crawl}")
        self._create_stat_csv()
        try:
            fetch_thread = threading.Thread(target=self.async_fetch_urls)
            fetch_thread.start()
            time.sleep(2)
            idle_counter = 0
            while True:
                if not self.pages_to_process:
                    logger.debug(f"Empty pages to process - ({idle_counter}) Sleep ...")
                    time.sleep(self.IDLE_WORK_SLEEP_INTERVAL)
                    idle_counter += 1
                    if idle_counter >= self.IDLE_COUNT_BEFORE_EXIT:
                        break
                    continue
                try:
                    page_to_process = self.pages_to_process.pop(0)
                    idle_counter = 0
                except IndexError:
                    continue
                self._crawl_iteration(page_to_process)
        except KeyboardInterrupt:
            logger.info("Crawler was stopped by user")
            self.stop_flag = True
        except Exception as e:
            logger.exception(e)
            logger.critical(f"Unexpected end of crawling - {e}")
        finally:
            logger.debug("Wait fetch thread to end ...")
            fetch_thread.join()
            logger.success(
                f"Crawl finished. Crawled pages: {self.crawl_count}. Time elapsed: {(datetime.datetime.now(datetime.timezone.utc) - self.start_time).seconds / 60 :.2f} min. Started from: {self.start_url_list}"
            )
            if self.error_processed_urls:
                logger.warning(
                    f"Unprocessed urls ({len(self.error_processed_urls)}): {self.error_processed_urls[:3]} ... {self.error_processed_urls[-3:]}"
                )
            self.db.save_to_db_to_disk()
            self.db.close()

    def _create_stat_csv(self):
        with open(STATISTICS_FILENAME, "w") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "iterations_count",
                    "link_between",
                    "link_word",
                    "url_list",
                    "word_list",
                    "word_location",
                ]
            )

    def async_fetch_urls(self):
        logger.debug("Starting fetch thread")
        try:
            asyncio.run(self.fetch_urls())
        except (KeyboardInterrupt, RuntimeError):
            logger.info("Finished fetch thread")

    async def fetch_urls(self):
        idle_counter = 0
        while True:
            if self.stop_flag:
                self.error_processed_urls.extend(self.urls_to_crawl)
                break

            if not self.urls_to_crawl:
                logger.debug(f"Empty urls to fetch ({idle_counter}). Sleeping ...")
                await asyncio.sleep(self.IDLE_WORK_SLEEP_INTERVAL)
                idle_counter += 1
                if idle_counter >= self.IDLE_COUNT_BEFORE_EXIT:
                    break
                continue

            urls_batch: List[LinkToGo] = self.urls_to_crawl[: self.FETCH_BATCH_SIZE]
            self.urls_to_crawl = self.urls_to_crawl[self.FETCH_BATCH_SIZE :]

            async def fetch(session: aiohttp.ClientSession, link: LinkToGo):
                retries_count = 0
                while retries_count < self.FETCH_MAX_RETRIES_COUNT:
                    try:
                        async with session.get(link.link) as response:
                            text = await response.text()
                            logger.debug(f"Fetched {link.link}")
                            return FetchedUrl(
                                url=link.link, text=text, depth=link.depth
                            )
                    except (
                        aiohttp.ServerTimeoutError,
                        aiohttp.ServerConnectionError,
                        aiohttp.ClientConnectionError,
                        asyncio.exceptions.TimeoutError,
                    ) as e:
                        retries_count += 1
                        logger.warning(f"{link.link} - {repr(e)} - {retries_count}")
                        await asyncio.sleep(self.FETCH_EXCEPTION_SLEEP_INTERVAL)
                    except (aiohttp.TooManyRedirects, UnicodeDecodeError):
                        break
                    except Exception as e:
                        logger.error(e)
                        break

                self.error_processed_urls.append(link.link)
                logger.error(f"Max retries exceed - {link.link}")
                return FetchedUrl(url="", text="")

            timeout = aiohttp.ClientTimeout(
                total=self.FETCH_TOTAL_TIMEOUT, connect=self.FETCH_CONNECT_TIMEOUT
            )
            async with aiohttp.ClientSession(timeout=timeout) as session:
                results: List[FetchedUrl] = await asyncio.gather(
                    *[fetch(session, url) for url in urls_batch], return_exceptions=True
                )
                results = [result for result in results if result.text]
                self.pages_to_process.extend(results)

            logger.info(
                f"End fetch iteration (batch={self.FETCH_BATCH_SIZE}). "
                f"len_urls_to_fetch={len(self.urls_to_crawl)} "
                f"len_pages_to_process={len(self.pages_to_process)}"
            )
            idle_counter = 0
            await asyncio.sleep(self.IDLE_WORK_SLEEP_INTERVAL)

        logger.info("Finishing fetch thread ...")

    def _crawl_iteration(self, fetched_url: FetchedUrl):
        if self.crawl_count and self.crawl_count % self.STAT_INTERVAL == 0:
            self.db.fill_stat(self.crawl_count)
        self.crawl_count += 1
        logger.debug(
            f"{self.crawl_count} - Processing {fetched_url.url} ({fetched_url.depth}) ..."
        )

        if not fetched_url.text:
            return

        elements = self.parser.parse_text_elements(fetched_url.text)

        try:
            fetched_url_id = self.db.insert_url(fetched_url.url)
            self.db.insert_links_from_elements(elements)
            self.db.insert_words_from_elements(elements)
            self.db.insert_links_between_by_elements(elements, fetched_url_id)
            self.db.fill_words_locations_by_elements(elements, fetched_url_id)
            self.db.fill_link_words_by_elements(elements)

            self.crawled_urls.append(fetched_url.url)

            if fetched_url.depth + 1 > self.MAX_DEPTH:
                return

            links_to_go_next = [
                LinkToGo(element.href, fetched_url.depth + 1)
                for element in elements
                if element.href and element.href not in self.crawled_urls
            ]

            self.urls_to_crawl.extend(links_to_go_next)
            self.urls_to_crawl = list(dict.fromkeys(self.urls_to_crawl))
        except SQLAlchemyError as e:
            logger.warning(
                f"Failed to write to DB {fetched_url.url} {fetched_url.depth} - {e}"
            )
            self.error_processed_urls.append(fetched_url.url)


class Parser:
    def parse_text_elements(self, text: str) -> List[Element]:
        soup = BeautifulSoup(text, "html.parser")

        for data in soup(["style", "script", "meta", "template"]):
            data.decompose()

        for element in soup(
            text=lambda text: isinstance(text, Comment)
        ):  # remove html comments
            element.extract()

        return self._parse_tags(tags=soup.find_all())

    def _parse_tags(self, tags: List[bs4.Tag]) -> List[Element]:
        output_elements: List[Element] = []

        for tag in tags:
            tag_text = tag.find(text=True, recursive=False)
            if tag_text is None:
                continue
            words = self._text_to_words(tag_text)
            href = ""
            if tag.name == "a":
                href = tag.get("href")
                if not (href is None):
                    if (
                        "mailto:" in href
                        or "tel:" in href
                        or href.endswith((".jpg", ".png", ".gif", ".jpeg", ".pdf"))
                        or not href.startswith("http")
                    ):
                        href = ""
                    href = href.strip("/")

            for i, word in enumerate(words, start=len(output_elements)):
                output_elements.append(Element(word=word, location=i, href=href))

        return output_elements

    def _text_to_words(self, text: str) -> List[str]:
        words = list(filter(None, re.split("[\W\d]+", text, flags=re.UNICODE)))
        for i, word in enumerate(words):
            words[i] = word.lower()
        return words
