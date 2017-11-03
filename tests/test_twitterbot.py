#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os
import datetime
import sqlite3


# change working directory for relative paths in the main modules to work as well as
# to be able to import them
os.chdir("..")
import youtube_search
import twitterbot


class SearchTermIndexTestCase(unittest.TestCase):
    """Test cases for modifying the search term index and links data in the database."""

    @classmethod
    def setUpClass(self):
        """Set up a test database with dummy data."""
        self.app = twitterbot.Bot("./test.db")

        with self.app.con:
            self.app.cur.execute("CREATE TABLE search_terms(search_term TEXT)")
            self.app.cur.execute("CREATE TABLE links(url TEXT, date TEXT, title TEXT, views INTEGER)")

    @classmethod
    def tearDownClass(self):
        os.remove("./test.db")

    def testFilledAfterRefresh(self):
        """Is the search term index non empty after a refresh?"""
        self.app.refresh_index()
        with self.app.con:
            self.app.cur.execute("SELECT COUNT(search_term) FROM search_terms")
            response = self.app.cur.fetchone()

        self.assertNotEqual(response, [0], "index is empty")

    def testSearchTermPop(self):
        """Test whether
        1 reading search terms from the index also removes them
        2 further attempt raises an error
        """
        # initialize the index with dummy data
        with self.app.con:
            self.app.cur.execute("DELETE FROM search_terms")
            dummy_search_terms = [("agamemnon",), ("molenCia",), ("hardly different",)]
            self.app.cur.executemany("INSERT INTO search_terms VALUES (?)", dummy_search_terms)

        search_terms = self.app.get_search_term_slice(3)

        # get the size of the index
        with self.app.con:
            self.app.cur.execute("SELECT COUNT(search_term) FROM search_terms")
            size = self.app.cur.fetchone()[0]
        self.assertEqual(size, 0, "Items were not removed from the search term index")

        # next call to get_search_term_slice should raise an error
        self.assertRaises(twitterbot.IndexEmptyException, self.app.get_search_term_slice, 1)

    def testRefreshedAfterSliceOnEmpty(self):
        """Is the search term index automatically filled if trying to pop from empty table?"""
        # empty the index
        with self.app.con:
            self.app.cur.execute("DELETE FROM search_terms")

        # attempt to read from the index, should result in a refresh
        self.app.parse_new_links(5)

        # get the size of the index
        with self.app.con:
            self.app.cur.execute("SELECT COUNT(search_term) FROM search_terms")
            response = self.app.cur.fetchone()

        self.assertNotEqual(response, [0], "Index did not get refreshed on empty")
