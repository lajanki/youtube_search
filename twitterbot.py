#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uses youtube_search.py to parse for links to zero view items and tweets them one at a time.
"""

import os
import json
import twython
import argparse
import logging
import sqlite3
import codecs
import youtube_search




# silence verbose http logging done by requests via urllib3
requests_log = logging.getLogger("requests")
requests_log.addHandler(logging.NullHandler())
requests_log.propagate = False

urlib_log = logging.getLogger("urllib3")
urlib_log.addHandler(logging.NullHandler())
urlib_log.propagate = False

# setup actual loggig
logging.basicConfig(
	filename = "bot.log",
	format = "%(asctime)s %(message)s",
	datefmt = "%d.%m.%Y %H:%M:%S",
	level = logging.INFO
)
logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    def create_tables(self):
        """Initialize the bot by creating a link storage database with a search term index table."""
        with self.con:
            self.cur.execute("CREATE TABLE IF NOT EXISTS search_terms(search_term TEXT)")
            self.cur.execute("CREATE TABLE IF NOT EXISTS links(url TEXT, date TEXT, title TEXT, views INTEGER)")

        self.refresh_index()

    def refresh_index(self):
        """Refill the index table from dict.txt. Drops previous data."""
        with codecs.open("./dict.txt", encoding="utf-8") as f:
            search_terms = f.read().splitlines()
            search_terms = [(item,) for item in search_terms]  # format as list of tuples to be able to pass to executemany

        with self.con:
            self.cur.execute("DELETE FROM search_terms")
            self.cur.executemany("INSERT INTO search_terms VALUES (?)", search_terms)

    def parse_new_links(self, n):
        """Use the crawler to search for zero view videos and store them in the database.
        Args:
            n (int): number of items to parse: n/2 search terms are picked from the index and n/2 are randomly generated
        """
        crawler = youtube_search.VideoCrawler()
        try:
            search_term_slice = self.get_search_term_slice(n/2)
            randomized = crawler.generate_random_search_terms(n/2, 2)
            search_terms = search_term_slice + randomized
            zeros = crawler.zero_search(search_terms)

            # Add new links to the database
            if zeros:
                links = [ (item["url"], item["date"], item["title"], item["views"]) for item in zeros ]
                with self.con:
                    self.cur.executemany("INSERT INTO links VALUES (?, ?, ?, ?)", links)
                    logger.info("Added {} new links to the database".format(len(zeros)))

            else:
              logger.info("No new links detected")

        # refresh (but don't do any parsing), on empty index
        except IndexEmptyException as err:
            logger.info("search term index is empty, refreshing")
            self.refresh_index()

    def get_search_term_slice(self, n):
        """Return a random sample of n search terms from the database."""
        with self.con:
            self.cur.execute("SELECT search_term FROM search_terms ORDER BY RANDOM() LIMIT {}".format(n))
            search_terms = self.cur.fetchall()

            # raise an error if there are no search terms left in the index
            if not search_terms:
                raise IndexEmptyException()

            # delete the items from the database
            self.cur.executemany("DELETE FROM search_terms WHERE search_term = ?", search_terms)

        return [item[0] for item in search_terms]  # return a flattened list of the search terms

    def get_link(self):
        """Choose a random link form the database."""
        browser = youtube_search.VideoBrowser()
        with self.con:
            # keep popping items from the database until we find one which still has no views or
            # until the table is empty
            views = 1
            while views:
                self.cur.execute("SELECT rowid, * FROM links ORDER BY RANDOM() LIMIT 1")
                row = self.cur.fetchone()

                if not row:
                    raise IndexError("No links in the database")

                rowid = row[0]
                url = row[1]

                # requery the view count from YouTube
                vid_id = url.split("?v=")[1]  # get the id from the url
                stats = browser.get_stats(vid_id)
                views = stats["views"]

                # delete the item from the table regardless of the current view count
                self.cur.execute("DELETE FROM links WHERE rowid = ?", (rowid,))

            return (row[1], row[2], row[3], row[4])

    def tweet(self):
        """Attempts to tweet the topmost item from the links database. Prints an error message if
        there is nothing to tweet.
        """
        with open("./keys.json") as f:
          keys = json.load(f)

        API_KEY = keys["TWITTER_API_KEY"]
        API_SECRET = keys["TWITTER_API_SECRET"]
        OAUTH_TOKEN = keys["TWITTER_OAUTH_TOKEN"]
        OAUTH_SECRET = keys["TWITTER_OAUTH_SECRET"]
        twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

        try:
            link = self.get_link()
            url = link[0]
            date = link[1]
            title = link[2]
            views = link[3]

            """
            Format a message to tweet:
            for long tweets, cut the title to 75 characters
            url = 23 characters (after Twitter's own link shortening, see https://support.twitter.com/articles/78124)
            date = 20
            views ~ 8
            linebreaks = 3
            => title: first 70 characters + "..."
            """
            if len(title) > 75:
                title = title[:72] + "..."

            msg = u"{}\n{}\nuploaded: {}\nviews: {}".format(title, url, date, views)

            # Encode the message for network I/O
            msg = msg.encode("utf8")
            twitter.update_status(status = msg)

        except IndexError as err:
            logger.error("links table is empty, nothing to tweet")
        except twython.exceptions.TwythonError as err:
            logger.error(err)
            print err

    def get_status(self):
        """Get the number of links and search terms in the database"""
        with self.con:
            self.cur.execute("SELECT COUNT(*) FROM links")
            nlinks = self.cur.fetchone()[0]

            self.cur.execute("SELECT COUNT(*) FROM search_terms")
            nindex = self.cur.fetchone()[0]

        return {"links": nlinks, "index": nindex}


class IndexEmptyException:
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
    parser.add_argument("--tweet", help = "Tweet the next result stored in links.json.", action = "store_true")
    parser.add_argument("--parse", help = "Parse n next search terms from search_terms.json for zero view items and store them to links.json.", metavar = "n", type = int)
    parser.add_argument("--stats", help = "Prints number of items left in links.json and index.json", action = "store_true")
    parser.add_argument("--init", help = "Initialize the bot by creating a file structure in bot-data/", action = "store_true")
    args = parser.parse_args()
    bot = Bot("bot-data/links.db")

    if args.init:
        bot.create_tables()

    elif args.tweet:
        bot.tweet()

    elif args.parse:
        logging.info("Parsing new links")
        bot.parse_new_links(args.parse)

    elif args.stats:
        stats = bot.get_status()
        print "{} links in links.json and {} search terms in index.json".format(stats["links"], stats["index"])
