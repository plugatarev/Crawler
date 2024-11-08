from src.crawler import start_crawler
from src.rankerer import calculate_ranks
from src.flask import run_flask 

import argparse

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("command", metavar="<command [start_crawler, calculate_ranks, run_flask]>", type=str,
                    help="Available commands: start_crawler, calculate_ranks, run_flask", )

args = parser.parse_args()

COMMANDS_MAPPING = {
    "start_crawler": start_crawler,
    "run_flask": run_flask,
    "calculate_ranks": calculate_ranks,
}

command = COMMANDS_MAPPING.get(args.command)

if not command:
    print(
        f"Available commands: start_crawler, calculate_ranks, run_flask.\nGot: {args.command}")
    exit(1)

command()
