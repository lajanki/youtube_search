#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Twitter bot. Depending on command line arguments either tweets a link from the database or searches Youtube API
for new zero view items. 
"""

import os
import argparse
import logging

from src import twitterbot


logger = logging.getLogger(__name__)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tweets links to YouTube videos with no views.")
    parser.add_argument(
        "--tweet", help="Tweet the next result stored in the database", action="store_true")
    parser.add_argument(
        "--parse", help="Choose n random search terms from the database and parse for zero view videos. Stores valid links to the database.",
        metavar="n", type=int)
    parser.add_argument(
        "--parse-if-low", help="Parse new links if less than threshold links left in the database",
        nargs=2, metavar=("n", "threshold"), type=int)
    parser.add_argument(
        "--status", help="Display the number of links and search terms left in the database.", action="store_true")
    parser.add_argument(
        "--init", help="Initialize the bot by creating a file structure in bot-data/", action="store_true")
    args = parser.parse_args()


    BASE = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(BASE, "bot-data", "links.db")
    bot = twitterbot.Bot(path)

    if args.init:
        bot.setup()

    elif args.tweet:
        bot.tweet()

    elif args.parse:
        logger.info("Parsing new links.")
        bot.parse_new_links(args.parse)

    elif args.parse_if_low:
        logger.info("Parsing new links.")
        links_left = bot.storage_writer.get_status()["links"]
        if links_left >= args.parse_if_low[1]:
            print("{} links left in the database, no parsing done.".format(links_left))
        else:
            bot.parse_new_links(args.parse_if_low[0])

    elif args.status:
        status = bot.storage_writer.get_status()
        print("{} links and {} search terms left in the database.".format(
            status["links"], status["index_size"]))