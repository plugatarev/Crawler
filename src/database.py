import csv
import itertools
import os
from typing import List, Tuple

import sqlalchemy
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.entity import Element, WordLocationsCombination
from src.settings import DATABASE_FILENAME, IGNORED_WORDS


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
        fkWordId INT,
        fkUrlId INT,
        location INT
    )
    """
    CREATE_TABLE_LINK_BETWEEN_URL = """
    -- откуда-куда ссылки
    CREATE TABLE IF NOT EXISTS link_between_url (
        linkId INTEGER PRIMARY KEY,
        fkFromUrlId INT,
        fkToUrlId INT
    )
    """
    CREATE_TABLE_LINK_WORD = """
    -- таблица слов использующихся в ссылках (tag 'a')
    CREATE TABLE IF NOT EXISTS link_word (
        id INTEGER PRIMARY KEY,
        fkWordId INT,
        fkLinkId INT
    )
    """

    SELECT_TABLES_COUNT = """
    SELECT COUNT(name) FROM sqlite_master WHERE type='table'
    """

    TOTAL_TABLES_COUNT = 5

    @classmethod
    def initialize_db(cls, session) -> None:
        session.execute(cls.CREATE_TABLE_WORD_LIST)
        session.execute(cls.CREATE_TABLE_URL_LIST)
        session.execute(cls.CREATE_TABLE_WORD_LOCATION)
        session.execute(cls.CREATE_TABLE_LINK_BETWEEN_URL)
        session.execute(cls.CREATE_TABLE_LINK_WORD)

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

    INSERT_INTO_URL_LIST_TURBO = """
    INSERT INTO url_list(url) VALUES {list_of_values}
    """

    INSERT_INTO_WORD_LIST = """
    INSERT INTO word_list(word) VALUES ('{word}')
    """

    INSERT_INTO_WORD_LIST_TURBO_FAST = """
    INSERT INTO word_list(word) VALUES {list_of_values}
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

    SELECT_LAST_LINK_ID = """
    SELECT MAX(urlId) FROM url_list
    """

    SELECT_TABLE_SIZE_STATS = """
    SELECT COUNT(*), 'link_between' as temp_field FROM link_between_url
    UNION
    SELECT COUNT(*), 'link_word' as temp_field FROM link_word
    UNION
    SELECT COUNT(*), 'url_list' as temp_field FROM url_list
    UNION
    SELECT COUNT(*), 'word_list' as temp_field FROM word_list
    UNION
    SELECT COUNT(*), 'word_location' as temp_field FROM word_location
    """

    GET_UNIQUE_WORDS_COUNT = """
    SELECT COUNT(unique_word) from
    (SELECT DISTINCT word as unique_word FROM word_list)
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

    @staticmethod
    def append_csv_stat(data: List[Tuple[str, int]], urls_crawled: int):
        with open(
            "stat.csv", "a", newline=""
        ) as csv_file:  # todo remove newline in linux
            writer = csv.writer(csv_file)
            writer.writerow(
                (
                    urls_crawled,
                    data[0][1],
                    data[1][1],
                    data[2][1],
                    data[3][1],
                    data[4][1],
                    data[5][1],
                )
            )

    def fill_stat(self, urls_crawled: int):
        result = self.db.execute(self.SELECT_TABLE_SIZE_STATS)
        result = result.fetchall()
        data = []
        for row in result:
            data.append((row[1], row[0]))

        unique_words_count = self.db.execute(self.GET_UNIQUE_WORDS_COUNT)
        unique_words_count = unique_words_count.fetchone()[0]
        data.append(("unique_words_count", unique_words_count))

        # logger.success(
        #     f'\n\tCrawled count: {urls_crawled}\n{tabulate(data, headers=["table_name", "rows"])}'
        # )
        self.append_csv_stat(data, urls_crawled)

    def _get_last_word_id(self) -> int:
        result = self.db.execute(self.SELECT_LAST_WORD_ID)
        result = result.fetchone()[0]
        return result

    def _get_last_url_id(self) -> int:
        result = self.db.execute(self.SELECT_LAST_LINK_ID)
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
        last_url_id = self._get_last_url_id() or 0
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
        self.db.execute(
            self.INSERT_INTO_URL_LIST_TURBO.format(list_of_values=list_of_values)
        )
        self.db.commit()

    def insert_words_from_elements(self, elements: List[Element]) -> None:
        last_word_id = self._get_last_word_id() or 0
        values_list = ""
        for element in elements:
            if not element.word:
                continue
            safe_word = element.word.replace("'", "")
            if safe_word in IGNORED_WORDS:
                continue
            values_list += f"('{safe_word}'),"
            last_word_id += 1
            element.word_id = last_word_id
        values_list = values_list.strip(",")
        self.db.execute(
            self.INSERT_INTO_WORD_LIST_TURBO_FAST.format(list_of_values=values_list)
        )
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
            values_list += f"({element.word_id}, {url_id}, {element.location}),"
        values_list = values_list.strip(",")
        query = self.INSERT_INTO_WORD_LOCATIONS.format(list_of_values=values_list)
        self.db.execute(query)
        self.db.commit()

    def fill_link_words_by_elements(self, elements: List[Element]):
        list_of_values = ""
        for element in elements:
            if element.word and element.href:
                list_of_values += f"({element.word_id}, {element.link_id}),"
        list_of_values = list_of_values.strip(",")
        if not list_of_values:
            return
        query = self.INSERT_INTO_LINK_WORD.format(list_of_values=list_of_values)
        self.db.execute(query)
        self.db.commit()

    def get_unique_urls_ids(self) -> List[int]:
        result = self.db.execute(self.SELECT_UNIQUE_URL_IDS)
        results = result.fetchall()
        result = list(zip(*results))
        return result[0]

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
            query += f", {word}"
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

        result = self.db.execute(query).fetchall()
        self.db.commit()

        combinations_list = []
        for i in result:
            locations_list = []
            for j in range(len(i) - 1):
                locations_list.append(i[j + 1])
            combinations_list.append(WordLocationsCombination(i[0], locations_list))

        return combinations_list