from random import randint

from airium import Airium

from src.database import DbActor


class FancyHTMLer:
    def __init__(self) -> None:
        self.db = DbActor()

    def create_marked_html_file(self, marked_html_filename, words, marked_words):
        marked_set = {}
        for i in tuple(marked_words):
            rand_color = "%06x" % randint(0, 0xFFFFFF)
            marked_set[i] = rand_color

        doc_gen = Airium(source_minify=True)

        with doc_gen.html("lang=ru"):
            with doc_gen.head():
                doc_gen.meta(charset="utf-8")
                doc_gen.title(_t="Marked Words Test")
            with doc_gen.body():
                with doc_gen.p():
                    for i in words:
                        if i not in marked_words:
                            doc_gen(f"{i}")
                        else:
                            with doc_gen.span(
                                style=f"background-color:#{marked_set[i]}"
                            ):
                                doc_gen(f"{i}")
                        doc_gen(" ")

        html = str(doc_gen)
        with open("search_results/" + marked_html_filename, "wb") as f:
            f.write(bytes(html, encoding="utf8"))

    def close(self) -> None:
        self.db.close()
