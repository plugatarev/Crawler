import glob

from flask import Flask, Response, redirect, render_template, request
from src.searcher import Searcher

app = Flask(__name__, template_folder=".." + "/search_results")


@app.get("/")
def index():
    return """
    <form action="/get_results">
        <label for="query">Search query:</label><br>
        <input type="text" id="query" name="query"><br>
        <input type="submit" value="Search">
    </form>
    """


@app.get("/get_results")
def get_results():
    query = request.args.get("query")
    Searcher().search(query)
    return redirect("/results")


@app.get("/results")
def results():
    file_names = glob.glob("search_results/" + "result_*")
    if not file_names:
        html = "<h1>Not found</h1>"
        return html
    html = ""
    file_names = sorted(file_names, reverse=True)
    for name in file_names:
        name = name.removeprefix("search_results").removeprefix("\\").removeprefix("/")
        html += f'<a href="/{name}">{name}</a><br>'
    return html


@app.get("/<filename>")
def render(filename: str):
    if filename == "favicon.ico":
        return Response(status=404)
    return render_template(filename)


def run_flask():
    app.run()
