#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
A Twitter bot for posting zero view YouTube links.
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


logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# silence verbose http logging done by YouTube connection
logging.getLogger("googleapiclient").setLevel(logging.ERROR)


class Bot(object):
    def __init__(self, path):
        self.crawler = youtube_search.VideoCrawler()
        self.twitter_client = Bot.create_client()
        self.storage_writer = StorageWriter(path)

    @staticmethod
    def create_client():
        with open("./keys.json") as f:
            keys = json.load(f)

        try:
            API_KEY = keys["TWITTER_API_KEY"]
            API_SECRET = keys["TWITTER_API_SECRET"]
            OAUTH_TOKEN = keys["TWITTER_OAUTH_TOKEN"]
            OAUTH_SECRET = keys["TWITTER_OAUTH_SECRET"]
            twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
        except KeyError:
            raise KeyError("Missing Twitter API key in keys.json")

        return twitter

    def setup(self):
        """Initialize the bot by creating a database with tables for search terms and valid links found."""
        self.storage_writer.create_tables()
        self.storage_writer.refresh_index()

    def parse_new_links(self, n):
        """Perform a YouTube search for zerp view items and store results to the database. Search terms are read
        from the search term index table.
        Args:
            n (int): number of search terms to use.
        """
        try:
            search_terms = self.storage_writer.fetch_random_search_term_batch(n)
            zeros = self.crawler.zero_search(search_terms)

            # Add new links to the database
            if zeros:
                links = [(item.url, item.publish_date, item.title, item.views)
                         for item in zeros]
                self.storage_writer.insert_links(links)
                logger.info("Added {} new links to the database.".format(len(zeros)))

            else:
                logger.info("No new links detected.")

        # refresh (but don't do any parsing), on empty index
        except IndexEmptyException:
            logger.info("search term index is empty, refreshing.")
            self.storage_writer.refresh_index()

    def get_link(self):
        """Fetch a link from the database to tweet. Since it's possible that the
        selected YouTube video may have received views since it was stored to the database,
        each item is rechedked for views are possibly discarded. In such case a new
        link is picked.
        TODO: check for empty link storage
        """
        views = 1
        while views:
            link = self.storage_writer.fetch_link()
            vid_id = link.url.split("?v=")[1]  # get the id from the url
            views = self.crawler.get_views(vid_id)

        return link

    def tweet(self):
        """Attempts to tweet the topmost item from the links database. Prints an error message if
        there is nothing to tweet.
        """
        try:
            link = self.get_link()

            """
            Format a message to tweet:
            for long tweets, cut the title to 75 characters
            url = 23 characters (after Twitter's own link shortening, see https://support.twitter.com/articles/78124)
            date = 20
            views ~ 8
            linebreaks = 3
            => title: first 70 characters + "..."
            """
            title = link.title
            if len(title) > 75:
                title = link.title[:72] + "..."

            msg = "{}\n{}\nuploaded: {}".format(
                title, link.url, link.publish_date)

            # Encode the message for network I/O
            msg = msg.encode("utf8")
            logger.info(msg)
            self.twitter_client.update_status(status=msg)
            print(msg)

        except IndexEmptyException as err:
            logger.error("links table is empty, nothing to tweet")
        except twython.exceptions.TwythonError as err:
            logger.error(err)
            print(err)


class StorageWriter(object):
    """A helper class for accessing the bot status database. The database contains 2 tables:
        search_terms: a dynamic index of search terms. Search terms are read from chunks of n
            words and the index is refresh once empty.
        link: cache for valid zero view items detected. Links are tweeted until the cache is empty
            and the next batch of search terms is processed.
    """

    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    def create_tables(self):
        """Create database tables for the search term index and valid YouTube links detected.
        The search term index is dynamic table used as a source for the search terms. It is initialized from
        common.txt.
        """
        with self.con:
            self.cur.execute("CREATE TABLE IF NOT EXISTS search_terms(search_term TEXT)")
            self.cur.execute(
                "CREATE TABLE IF NOT EXISTS links(url TEXT, date TEXT, title TEXT, views INTEGER)")

    def refresh_index(self):
        """Fill the search term index from common.txt. Drops previous data."""
        with codecs.open("./common.txt", encoding="utf-8") as f:
            search_terms = f.read().splitlines()
            # format as list of tuples to be able to pass to executemany
            search_terms = [(item,) for item in search_terms]

        with self.con:
            self.cur.execute("DELETE FROM search_terms")
            self.cur.executemany("INSERT INTO search_terms VALUES (?)", search_terms)

    def fetch_random_search_term_batch(self, n):
        """Return a random sample of n search terms from the index. The selected
        batch is removed from the index.
        Args:
            n (int): number of search terms to read
        Return:
            a list of search terms
        """
        with self.con:
            self.cur.execute(
                "SELECT search_term FROM search_terms ORDER BY RANDOM() LIMIT {}".format(n))
            search_terms = self.cur.fetchall()

            # raise an error if there are no search terms left in the index
            if not search_terms:
                raise IndexEmptyException("Search term index is empty")

            # delete the items from the index
            self.cur.executemany("DELETE FROM search_terms WHERE search_term = ?", search_terms)

        return [item[0] for item in search_terms]

    def insert_links(self, links):
        """INSERT a list of links into the links table. Each link is a tuple of
        (url, publish_date, title, viewcount)
        """
        with self.con:
            self.cur.executemany("INSERT INTO links VALUES (?, ?, ?, ?)", links)

    def fetch_link(self):
        """Fetch a random link form the database. The selected item is removed from the table.
        Return:
            youtube_search.VideoResult instance matching the database row selected
        """
        with self.con:
            self.cur.execute("SELECT rowid, * FROM links ORDER BY RANDOM() LIMIT 1")
            row = self.cur.fetchone()

            if not row:
                raise IndexEmptyException("No links in the database")

            rowid = row[0]
            self.cur.execute("DELETE FROM links WHERE rowid = ?", (rowid,))

        return youtube_search.VideoResult(title=row[3], url=row[1], views=row[4], publish_date=row[2])

    def get_status(self):
        """Get the number of links and search terms in the database."""
        with self.con:
            self.cur.execute("SELECT COUNT(*) FROM links")
            nlinks = self.cur.fetchone()[0]

            self.cur.execute("SELECT COUNT(*) FROM search_terms")
            nindex = self.cur.fetchone()[0]

        return {"links": nlinks, "index_size": nindex}


class IndexEmptyException(Exception):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search for and tweet Youtube videos with no or little views.")
    parser.add_argument(
        "--tweet", help="Tweet the next result stored in links.json.", action="store_true")
    parser.add_argument(
        "--parse", help="Parse n next search terms from search_terms.json for zero view items and store them to links.json.", metavar="n", type=int)
    parser.add_argument(
        "--stats", help="Prints number of items left in links.json and index.json", action="store_true")
    parser.add_argument(
        "--init", help="Initialize the bot by creating a file structure in bot-data/", action="store_true")
    args = parser.parse_args()

    # create a bot-data directory if it doesn't exist
    base = "bot-data"
    if not os.path.isdir(base):
        os.mkdir(base)
    path = os.path.join(base, "links.db")
    bot = Bot(path)

    if args.init:
        bot.setup()

    elif args.tweet:
        bot.tweet()

    elif args.parse:
        logger.info("Parsing new links")
        bot.parse_new_links(args.parse)

    elif args.stats:
        status = bot.storage_writer.get_status()
        print("{} links in links.json and {} search terms in index.json".format(
            status["links"], status["index_size"]))
