import csv
import itertools
import os
from typing import List, Tuple

import sqlalchemy
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.model import Element, ResultURL, PageRankURL, WordLocationsCombination
from src.settings import DATABASE_FILENAME, IGNORED_WORDS, STATISTICS_FILENAME


class DbCreator:
    CREATE_TABLE_WORD_LIST = """
    CREATE TABLE IF NOT EXISTS word_list (
        wordId INTEGER PRIMARY KEY,
        word TEXT
    )
    """
    CREATE_TABLE_URL_LIST = """
    CREATE TABLE IF NOT EXISTS url_list (
        urlId INTEGER PRIMARY KEY,
        url TEXT
    )
    """

    CREATE_TABLE_WORD_LOCATION = """
    CREATE TABLE IF NOT EXISTS word_location (
        id INTEGER PRIMARY KEY,
        fkWordId INT REFERENCES word_list(wordId) ON DELETE CASCADE ON UPDATE CASCADE,
        fkUrlId INT REFERENCES url_list(urlId) ON DELETE CASCADE ON UPDATE CASCADE,
        location INT
    )
    """
    CREATE_TABLE_LINK_BETWEEN_URL = """
    CREATE TABLE IF NOT EXISTS link_between_url (
        linkId INTEGER PRIMARY KEY,
        fkFromUrlId INT REFERENCES url_list(urlId) ON DELETE CASCADE ON UPDATE CASCADE,
        fkToUrlId INT REFERENCES url_list(urlId) ON DELETE CASCADE ON UPDATE CASCADE
    )
    """
    CREATE_TABLE_LINK_WORD = """
    CREATE TABLE IF NOT EXISTS link_word (
        id INTEGER PRIMARY KEY,
        fkWordId INT REFERENCES word_list(wordId) ON DELETE CASCADE ON UPDATE CASCADE,
        fkLinkId INT REFERENCES link_between_url(linkId) ON DELETE CASCADE ON UPDATE CASCADE
    )
    """
    CREATE_TABLE_PAGE_RANK = """
    CREATE TABLE IF NOT EXISTS page_rank (
        id INTEGER PRIMARY KEY,
        fkUrlId INT,
        rank REAL
    )
    """

    SELECT_TABLES_COUNT = """
    SELECT COUNT(name) FROM sqlite_master WHERE type='table'
    """

    SELECT_TOP_20_URLS = """
    SELECT url FROM 
        (SELECT url, count(*) as count FROM url_list GROUP BY url ORDER BY count DESC) 
    LIMIT 20
    """

    SELECT_TOP_20_WORDS = """
    SELECT word FROM 
        (SELECT word, count(*) as count FROM word_list GROUP BY word ORDER BY count DESC) 
    LIMIT 20
    """

    TOTAL_TABLES_COUNT = 6

    @classmethod
    def initialize_db(cls, session) -> None:
        session.execute(cls.CREATE_TABLE_WORD_LIST)
        session.execute(cls.CREATE_TABLE_URL_LIST)
        session.execute(cls.CREATE_TABLE_WORD_LOCATION)
        session.execute(cls.CREATE_TABLE_LINK_BETWEEN_URL)
        session.execute(cls.CREATE_TABLE_LINK_WORD)
        session.execute(cls.CREATE_TABLE_PAGE_RANK)

        result = session.execute(cls.SELECT_TABLES_COUNT)
        tables_count = result.fetchone()[0]
        if tables_count != cls.TOTAL_TABLES_COUNT:
            logger.critical(
                f"Not enougth tables! Need: {cls.TOTAL_TABLES_COUNT}. Got: {tables_count}"
            )
            exit(1)


class DbActor:
    INSERT_INTO_URL_LIST = """
    INSERT INTO url_list(url) VALUES ('{url}')
    """

    INSERT_INTO_URL_LIST_BATCH = """
    INSERT INTO url_list(url) VALUES {urls}
    """

    INSERT_INTO_WORD_LIST_BATCH = """
    INSERT INTO word_list(word) VALUES {words}
    """

    INSERT_INTO_WORD_LOCATIONS = """
    INSERT INTO word_location(fkWordId, fkUrlId, location) VALUES {list_of_values}
    """

    INSERT_INTO_LINKS_BETWEEN = """
    INSERT INTO link_between_url(fkFromUrlId, fkToUrlId) VALUES {list_of_values}
    """

    INSERT_INTO_LINK_WORD = """
    INSERT INTO link_word(fkWordId, fkLinkId) VALUES {list_of_values}
    """

    SELECT_LAST_WORD_ID = """
    SELECT MAX(wordId) FROM word_list
    """

    SELECT_LAST_URL_ID = """
    SELECT MAX(urlId) FROM url_list
    """

    SELECT_LINK_BETWEEN_STATS = """
    SELECT COUNT(*), 'link_between' as temp_field FROM link_between_url
    """

    SELECT_LINK_WORD_STATS = """
    SELECT COUNT(*), 'link_word' as temp_field FROM link_word
    """

    SELECT_URL_LIST_STATS = """
    SELECT COUNT(*), 'url_list' as temp_field FROM url_list
    """

    SELECT_WORD_LIST_STATS = """
    SELECT COUNT(*), 'word_list' as temp_field FROM word_list
    """

    SELECT_WORD_LOCATION_STATS = """
    SELECT COUNT(*), 'word_location' as temp_field FROM word_location
    """

    SELECT_UNIQUE_URL_IDS = """
    SELECT urlId FROM url_list GROUP BY url ORDER BY urlId
    """

    SELECT_ALL_REFERENCES_TO_URL_BY_ID = """
    SELECT fkFromUrlId FROM link_between_url WHERE fkToUrlId = {link_to_fk}
    """

    SELECT_ALL_WORDS_BY_URL = """
    SELECT word FROM word_list INNER JOIN word_location ON wordId = fkWordId where fkUrlId = {url_id}
    """

    GET_URL_LINK_COUNT = """
    SELECT COUNT(*) FROM link_between_url WHERE fkFromUrlId = {fk_from_url_id}
    """

    GET_UNIQUE_WORDS_COUNT = """
    SELECT COUNT(unique_word) from
    (SELECT DISTINCT word as unique_word FROM word_list)
    """

    SELECT_URL_IDS = """
    SELECT urlId FROM url_list ORDER BY urlId
    """

    INSERT_IN_RANGE_RANK_MAIN = """
    INSERT INTO page_rank(fkUrlId, rank) VALUES {list_of_values}
    """

    INSERT_IN_RANGE_RANK_TEMP = """
    INSERT INTO page_rank_temp(fkUrlId, rank) VALUES {list_of_values}
    """

    SELECT_ALL_REFERENCES_TO_URL_BY_ID = """
    SELECT fkFromUrlId FROM link_between_url WHERE fkToUrlId = {link_to_fk}
    """

    SELECT_ALL_WORDS_BY_URL = """
    SELECT word FROM word_list INNER JOIN word_location ON wordId = fkWordId where fkUrlId = {url_id}
    """

    SELECT_URL_RANK_INFO = """
    select url_id, ref_count, rank, from_url, from_rank / count_from from url_list
    inner join
    (select fkFromUrlId as url_id, count(fkFromUrlId) as ref_count from link_between_url
    where fkFromUrlId = {url_id}) as count_part
    on count_part.url_id = urlid
    inner join
    (select fkUrlId, rank from page_rank where fkUrlId = {url_id}) as rank_part
    on rank_part.fkUrlId = urlid
    inner join
    (select from_url, from_rank, count(*) as count_from, inner_to_part.fkToUrlId from (select distinct fkFromUrlId as from_url, page_rank.rank as from_rank, fkToUrlId from link_between_url
    inner join page_rank on from_url = page_rank.fkUrlId where fkToUrlId = {url_id}) as inner_to_part inner join link_between_url as lbu on lbu.fkFromUrlId = from_url GROUP by lbu.fkFromUrlId) as to_part
    on to_part.fkToUrlId = urlid
    """

    GET_URL_LINK_COUNT = """
    SELECT COUNT(*) FROM link_between_url WHERE fkFromUrlId = {fk_from_url_id}
    """

    GET_PAGE_RANK_BY_ID = """
    SELECT rank FROM page_rank WHERE id = {id_}
    """

    SET_PAGE_RANK_BY_ID = """
    INSERT INTO page_rank_temp(fkUrlId, rank) VALUES ({url_id}, {rank})
    """

    SYNC_TEMP_AND_MAIN_PAGE_RANKS = """
    UPDATE page_rank
    SET rank = (SELECT page_rank_temp.rank
                                FROM page_rank_temp
                                WHERE page_rank_temp.fkUrlId = page_rank.fkUrlId)
    """

    GET_PAGE_RANK_ONE_ROW = """
    SELECT * FROM page_rank LIMIT 1
    """

    SELECT_MAX_PAGE_RANK = """
    SELECT rank FROM page_rank ORDER BY rank DESC LIMIT 1
    """

    GET_URLS_WITH_PAGE_RANK_IN_URL_IDS = """
    SELECT url_list.urlId, url_list.url, page_rank.rank FROM url_list
    INNER JOIN page_rank ON url_list.urlId = page_rank.fkUrlId
    WHERE url_list.urlId IN {url_ids_list}
    """

    SQLALCHEMY_DATABASE_URL_MEMORY = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URL_FILE = f"sqlite:///{DATABASE_FILENAME}"

    def __init__(self) -> None:
        self.url_ids_dict = dict()

        # https://stackoverflow.com/questions/5831548/how-to-save-my-in-memory-database-to-hard-disk

        if DATABASE_FILENAME not in os.listdir():
            logger.info("Db in disk not found")

            # Open db in memory
            memory_engine = create_engine(self.SQLALCHEMY_DATABASE_URL_MEMORY)
            self.raw_connection_memory = memory_engine.raw_connection()
            DbSessionMemory = sessionmaker(autoflush=False, bind=memory_engine)
            memory_session_ = DbSessionMemory()

            # Create tables
            DbCreator.initialize_db(memory_session_)
            self.db = memory_session_
            return

        logger.info("Db in disk found")

        # Open db in memory
        memory_engine = create_engine(self.SQLALCHEMY_DATABASE_URL_MEMORY)
        raw_connection_memory = memory_engine.raw_connection()
        self.raw_connection_memory = raw_connection_memory
        DbSessionMemory = sessionmaker(autoflush=False, bind=memory_engine)
        memory_session_ = DbSessionMemory()

        file_engine = sqlalchemy.create_engine(self.SQLALCHEMY_DATABASE_URL_FILE)
        raw_connection_file = file_engine.raw_connection()
        raw_connection_file.backup(raw_connection_memory.connection)
        raw_connection_file.close()
        file_engine.dispose()

        self.db = memory_session_
        return

    def save_to_db_to_disk(self) -> None:
        engine_file = sqlalchemy.create_engine(self.SQLALCHEMY_DATABASE_URL_FILE)
        raw_connection_file = engine_file.raw_connection()
        self.raw_connection_memory.backup(raw_connection_file.connection)
        raw_connection_file.close()
        engine_file.dispose()

    def close(self):
        self.db.close()

    def fill_stat(self, urls_crawled: int):
        data = []

        result = self.db.execute(self.SELECT_LINK_BETWEEN_STATS)
        result = result.fetchall()
        data.append((result[0][1], result[0][0]))
        result = self.db.execute(self.SELECT_LINK_WORD_STATS)
        result = result.fetchall()
        data.append((result[0][1], result[0][0]))
        result = self.db.execute(self.SELECT_URL_LIST_STATS)
        result = result.fetchall()
        data.append((result[0][1], result[0][0]))
        result = self.db.execute(self.SELECT_WORD_LIST_STATS)
        result = result.fetchall()
        data.append((result[0][1], result[0][0]))
        result = self.db.execute(self.SELECT_WORD_LOCATION_STATS)
        result = result.fetchall()
        data.append((result[0][1], result[0][0]))

        self._append_csv_stat(data, urls_crawled)

    @staticmethod
    def _append_csv_stat(data: List[Tuple[str, int]], urls_crawled: int):
        with open(STATISTICS_FILENAME, "a", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                (
                    urls_crawled,
                    data[0][1],
                    data[1][1],
                    data[2][1],
                    data[3][1],
                    data[4][1],
                )
            )

    def _get_last_word_id(self) -> int:
        result = self.db.execute(self.SELECT_LAST_WORD_ID)
        result = result.fetchone()[0]
        return result

    def _get_last_url_id(self) -> int:
        result = self.db.execute(self.SELECT_LAST_URL_ID)
        result = result.fetchone()[0]
        return result

    def insert_url(self, url: str) -> int:
        already_in_db = self.db.execute(
            f"SELECT urlId FROM url_list WHERE url = '{url}'"
        ).fetchone()
        if already_in_db:
            return already_in_db[0]

        query = self.INSERT_INTO_URL_LIST.format(url=url)
        self.db.execute(query)
        row_id = self._get_last_insert_rowid()
        self.db.commit()
        self.url_ids_dict[url] = row_id
        return row_id

    def _get_last_insert_rowid(self) -> int:
        return self.db.execute("SELECT last_insert_rowid();").fetchall()[0][0]

    def insert_links_from_elements(self, elements: List[Element]) -> None:
        last_url_id = self._get_last_url_id() or 1
        list_of_values = ""

        for element in elements:
            if not element.href:
                continue
            if element.href not in self.url_ids_dict:
                last_url_id += 1
                self.url_ids_dict[element.href] = last_url_id
                list_of_values += f"('{element.href}'),"

        for element in elements:
            if not element.href:
                continue
            element.link_id = self.url_ids_dict[element.href]

        list_of_values = list_of_values.strip(",")
        if not list_of_values:
            return
        self.db.execute(self.INSERT_INTO_URL_LIST_BATCH.format(urls=list_of_values))
        self.db.commit()

    def insert_words_from_elements(self, elements: List[Element]) -> None:
        last_word_id = self._get_last_word_id() or 1
        values_list = ""
        unique_words = dict()
        for element in elements:
            if not element.word:
                continue
            safe_word = element.word.replace("'", "").strip()
            if safe_word in IGNORED_WORDS:
                continue
            if safe_word in unique_words.values():
                element.word_id = list(unique_words.keys())[
                    list(unique_words.values()).index(safe_word)
                ]
                continue
            already_in_db = self.db.execute(
                f"SELECT wordId FROM word_list WHERE word = '{safe_word}'"
            ).fetchone()
            if already_in_db:
                element.word_id = already_in_db[0]
                unique_words[already_in_db[0]] = safe_word
                continue
            values_list += f"('{safe_word}'),"
            last_word_id += 1
            element.word_id = last_word_id
            unique_words[last_word_id] = safe_word
        values_list = values_list.strip(",")
        if not values_list:
            return
        self.db.execute(self.INSERT_INTO_WORD_LIST_BATCH.format(words=values_list))
        self.db.commit()

    def insert_links_between_by_elements(
        self, elements: List[Element], original_link_id: int
    ) -> None:
        values_list = ""
        unique_urls = dict()
        for element in elements:
            if not element.href:
                continue
            unique_urls.setdefault(element.href, element.link_id)
        for unique_url_id in unique_urls.values():
            values_list += f"({original_link_id}, {unique_url_id}),"
        values_list = values_list.strip(",")
        if not values_list:
            return
        query = self.INSERT_INTO_LINKS_BETWEEN.format(list_of_values=values_list)
        self.db.execute(query)
        self.db.commit()

    def fill_words_locations_by_elements(self, elements: List[Element], url_id: int):
        values_list = ""
        for element in elements:
            if element.word_id == 0:
                continue
            values_list += f"({element.word_id}, {url_id}, {element.location}),"
        values_list = values_list.strip(",")
        if not values_list:
            return
        query = self.INSERT_INTO_WORD_LOCATIONS.format(list_of_values=values_list)
        self.db.execute(query)
        self.db.commit()

    def fill_link_words_by_elements(self, elements: List[Element]):
        list_of_values = ""
        for element in elements:
            if element.word and element.href and element.word_id != 0:
                list_of_values += f"({element.word_id}, {element.link_id}),"
        list_of_values = list_of_values.strip(",")
        if not list_of_values:
            return
        query = self.INSERT_INTO_LINK_WORD.format(list_of_values=list_of_values)
        self.db.execute(query)
        self.db.commit()

    def get_urls_ids(self) -> List[int]:
        result = self.db.execute(self.SELECT_URL_IDS)
        results = result.fetchall()
        result = list(zip(*results))
        return result[0]

    def fill_page_rank(self, page_ranks: List[PageRankURL]) -> None:
        self.db.execute("delete from page_rank")
        self.db.commit()

        list_of_values = ""
        for page in page_ranks:
            list_of_values += f"({page.id}, {page.rank}),"
        list_of_values = list_of_values.strip(",")
        self.db.execute(
            self.INSERT_IN_RANGE_RANK_MAIN.format(list_of_values=list_of_values)
        )
        self.db.commit()

    def fill_temp_page_rank(self, entities: List[PageRankURL]) -> None:
        list_of_values = ""
        for entity in entities:
            list_of_values += f"({entity.id}, {entity.rank}),"
        list_of_values = list_of_values.strip(",")
        self.db.execute(
            self.INSERT_IN_RANGE_RANK_TEMP.format(list_of_values=list_of_values)
        )
        self.db.commit()

    def get_from_urls_by_to(self, fk_to_url_id: int) -> List[int]:
        result = self.db.execute(
            self.SELECT_ALL_REFERENCES_TO_URL_BY_ID.format(link_to_fk=fk_to_url_id)
        )
        result = result.fetchall()
        return list(itertools.chain(*result))

    def get_from_url_count(self, fk_from_url_id: int) -> int:
        result = self.db.execute(
            self.GET_URL_LINK_COUNT.format(fk_from_url_id=fk_from_url_id)
        ).fetchone()[0]
        return result

    def get_page_rank_by_id(self, id_: int) -> float:
        result = self.db.execute(self.GET_PAGE_RANK_BY_ID.format(id_=id_)).fetchone()[0]
        return result

    def sync_main_and_temp_rank_tables(self) -> None:
        self.db.execute(self.SYNC_TEMP_AND_MAIN_PAGE_RANKS)
        self.db.commit()

    def get_words_by_url(self, url_id):
        result = self.db.execute(
            self.SELECT_ALL_WORDS_BY_URL.format(url_id=url_id)
        ).fetchall()
        return list(zip(*result))[0]

    # get combinations of all word locations from list on all avaliable urls
    # returns WordLocationsCombination or null if words not specified
    def get_words_location_combinations(self, words: List[str]):
        if len(words) == 0:
            return

        query = f"select {words[0]}_url as url"
        for i, word in enumerate(words):
            query += f", {word}_location"
        for i, word in enumerate(words):
            if i == 0:
                query += " from"
            else:
                query += " inner join"
            query += (
                f"(select {word}, fkurlid as {word}_url, location as {word}_location from word_location "
                f"inner join (select wordid as {word} from word_list where word = '{word}') as word{i} on word{i}.{word} = fkwordid) "
            )
            if i > 0:
                query += f"on {words[i-1]}_url = {words[i]}_url"

        # query = f"select {words[0]}_url as url, {words[0]}, {words[1]} from (select {words[0]}, fkurlid as {words[0]}_url, location as {words[0]}_location from word_location inner join (select wordid as {words[0]} from word_list where word = '{words[0]}') as word0 on word0.{words[0]} = fkwordid) inner join (select {words[1]}, fkurlid as {words[1]}_url, location as {words[1]}_location from word_location inner join (select wordid as {words[1]} from word_list where word = '{words[1]}') as word1 on word1.{words[1]} = fkwordid) on {words[0]}_url = {words[1]}_url"

        result = self.db.execute(query).fetchall()
        self.db.commit()

        combinations_list = []
        for i in result:
            locations_list = []
            for j in range(len(i) - 1):
                locations_list.append(i[j + 1])
            combinations_list.append(WordLocationsCombination(i[0], locations_list))

        return combinations_list

    def get_url_page_rank_info(self, url_id):
        result = self.db.execute(
            self.SELECT_URL_RANK_INFO.format(url_id=url_id)
        ).fetchall()
        return result

    def is_page_rank_table_empty(self) -> bool:
        result = self.db.execute(self.GET_PAGE_RANK_ONE_ROW)
        result = result.fetchone()
        if result is None:
            return True
        return False

    def get_max_page_rank(self) -> float:
        result = self.db.execute(self.SELECT_MAX_PAGE_RANK)
        result = result.fetchone()[0]
        return result

    def get_urls_with_page_ranks(self, url_ids: List[int]) -> List[ResultURL]:
        url_ids_list_str = str(url_ids).replace("[", "(").replace("]", ")")
        result = self.db.execute(
            self.GET_URLS_WITH_PAGE_RANK_IN_URL_IDS.format(
                url_ids_list=url_ids_list_str
            )
        )
        result = result.fetchall()

        return [
            ResultURL(
                url_id=row[0],
                url_name=row[1],
                page_rank_raw_metric=row[2],
            )
            for row in result
        ]
