from src.crawler import start_crawler

import argparse

parser = argparse.ArgumentParser(
    description="Search system!")

parser.add_argument("command", metavar="<command [start_crawler]>", type=str,
                    help="Available commands: start_crawler", )

args = parser.parse_args()


COMMANDS_MAPPING = {
    "start_crawler": start_crawler,
}

command = COMMANDS_MAPPING.get(args.command)

if not command:
    print(
        f"Available commands: start_crawler.\nGot: {args.command}")
    exit(1)

command()