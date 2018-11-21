#!/usr/bin/python
# -*- coding: utf-8 -*-


import json
import unittest
from unittest.mock import patch, mock_open

import youtube_search
import twitterbot


class BotTestCase(unittest.TestCase):

    @patch("youtube_search.VideoCrawler")
    @patch("twitterbot.Bot.create_client")
    @patch("twitterbot.StorageWriter")
    def setUp(self, mock_storage_writer, mock_create_client, mock_video_crawler):
        """Create a Bot instance and replace all its accessors with mocks."""
        self.bot = twitterbot.Bot("foo")

    def test_create_client_raises_error_on_missing_key(self):
        """Does create_client raise an error on missing key?"""
        invalid_keys = json.dumps({"foo": "bar"})
        with patch("builtins.open", mock_open(read_data=invalid_keys), create=True):
            self.assertRaises(KeyError, twitterbot.Bot.create_client)

    def test_parse_new_links_refreshes_index_if_empty(self):
        """Does parse_new_links call the index refresh method if there are no
        search terms left in the index?
        """
        self.bot.storage_writer.fetch_random_search_term_batch.side_effect = twitterbot.IndexEmptyException()
        self.bot.parse_new_links(1)

        self.bot.storage_writer.refresh_index.assert_called()

    def test_parse_new_links_inserts_links_into_database(self):
        """Does parse_new_links insert the detected links to the links table?"""
        res1 = youtube_search.VideoResult(
            title="Title", url="https://www.youtube.com/watch?v=id", views=0, publish_date="Nov 7, 2018")
        res2 = youtube_search.VideoResult(
            title="Title2", url="https://www.youtube.com/watch?v=id2", views=0, publish_date="Oct 2, 2016")
        self.bot.crawler.zero_search.return_value = [res1, res2]

        self.bot.parse_new_links(1)
        links = [(item.url, item.publish_date, item.title, item.views)
                 for item in [res1, res2]]
        self.bot.storage_writer.insert_links.assert_called_with(links)

    def test_get_link_rejects_upon_recheck(self):
        """Does get_link ignore links which are determined to have views upon recheck?"""
        link1 = youtube_search.VideoResult(
            title="Title", url="https://www.youtube.com/watch?v=id", views=0, publish_date="Nov 7, 2018")
        link2 = youtube_search.VideoResult(
            title="Title2", url="https://www.youtube.com/watch?v=id2", views=0, publish_date="Oct 2, 2016")
        # mock link storage to have 2 links
        self.bot.storage_writer.fetch_link.side_effect = [link1, link2]
        self.bot.crawler.get_views.side_effect = [1, 0]

        res = self.bot.get_link()
        self.assertEqual(str(res), str(link2))


class StorageWriterTestCase(unittest.TestCase):

    @patch("twitterbot.sqlite3.connect")
    def setUp(self, mock_connect):
        self.storage_writer = twitterbot.StorageWriter("foo")

    def test_refresh_index_clears_and_inserts_new_search_terms(self):
        """Does refresh_index clear the search term table and insert the ones read from
        the permanent search term file?
        """
        with patch("codecs.open", mock_open(read_data="foo\nbar\nbaz")):
            self.storage_writer.refresh_index()
            self.storage_writer.cur.execute.assert_called_with("DELETE FROM search_terms")
            self.storage_writer.cur.executemany.assert_called_with(
                "INSERT INTO search_terms VALUES (?)", [('foo',), ('bar',), ('baz',)])

    def test_fetch_random_search_term_batch_raises_error_on_empty_index(self):
        """Does calling fetch_random_search_term_batch result in an IndexEmptyException
        when the search term index table is empty?
        """
        self.storage_writer.cur.fetchall.return_value = None
        self.assertRaises(twitterbot.IndexEmptyException,
                          self.storage_writer.fetch_random_search_term_batch, 1)

    def test_fetch_random_search_term_batch_removes_chosen_batch(self):
        """Does calling fetch_random_search_term_batch remove the selected batch from
        the index?
        """
        self.storage_writer.cur.fetchall.return_value = ["foo", "bar", "baz"]

        self.storage_writer.fetch_random_search_term_batch(1)
        self.storage_writer.cur.executemany.assert_called_with(
            "DELETE FROM search_terms WHERE search_term = ?", ["foo", "bar", "baz"])

    def test_fetch_link_raises_error_on_empty_link_storage(self):
        """Does calling fetch_link result in an IndexEmptyException
        when there are no links left in the table?
        """
        self.storage_writer.cur.fetchone.return_value = None
        self.assertRaises(twitterbot.IndexEmptyException,
                          self.storage_writer.fetch_link)

    def test_fetch_link_removes_chosen_link(self):
        """Does calling fetch_link remove the selected link from the link storage?
        """
        self.storage_writer.cur.fetchone.return_value = [1, "https://www.youtube.com/watch?v=id",
                                                            "Nov 7, 2018", "Title", 0]
        self.storage_writer.fetch_link()

        self.storage_writer.cur.execute.assert_called_with(
            "DELETE FROM links WHERE rowid = ?", (1,))

    def test_fetch_link_returns_videoresult(self):
        """Does calling fetch_link return a youtube_search.VideoResult instance with
        values matching matching those on the database row?
        """
        self.storage_writer.cur.fetchone.return_value = [1, "https://www.youtube.com/watch?v=id",
                                                         "Nov 7, 2018", "Title", 0]
        res = self.storage_writer.fetch_link()
        asserted_response = youtube_search.VideoResult(
            title="Title", url="https://www.youtube.com/watch?v=id", views=0, publish_date="Nov 7, 2018")

        self.assertEqual(str(res), str(asserted_response))


if __name__ == "__main__":
    """Create test suites from both classes and run tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(StorageWriterTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)

    suite = unittest.TestLoader().loadTestsFromTestCase(BotTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
