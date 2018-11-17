#!/usr/bin/python
# -*- coding: utf-8 -*-


import datetime
import unittest
import json
from unittest.mock import patch, mock_open

import youtube_search


class VideoCrawlerTestCase(unittest.TestCase):
    """Test cases for searching zero view videos."""

    @patch("youtube_search.VideoCrawler.create_client")
    def setUp(self, mock_create_client):
        self.crawler = youtube_search.VideoCrawler()
        self.search_response_json_string = """{
         "kind": "youtube#searchListResponse",
         "etag": "XI7nbFXulYBIpL0ayR_gDh3eu1k/VGqBSVauZBhlTNwqV9NaLOyo2-U",
         "nextPageToken": "CAMQAA",
         "regionCode": "FI",
         "pageInfo": {
          "totalResults": 1000000,
          "resultsPerPage": 3
         },
         "items": [
          {
           "kind": "youtube#searchResult",
           "etag": "XI7nbFXulYBIpL0ayR_gDh3eu1k/134tLvMh5ow5iBeBllpGwtxpjoY",
           "id": {
            "kind": "youtube#video",
            "videoId": "EQ1HKCYJM5U"
           },
           "snippet": {
            "publishedAt": "2009-08-20T16:04:07.000Z",
            "channelId": "UCCj956IF62FbT7Gouszaj9w",
            "title": "Funny Talking Animals - Walk On The Wild Side - Episode Three Preview - BBC One",
            "description": "SUBSCRIBE for more BBC highlights: https://bit.ly/2IXqEIn http://www.bbc.co.uk/comedy Walk On The Wild Side is a brand new comedy series that seeks to ...",
            "thumbnails": {
             "default": {
              "url": "https://i.ytimg.com/vi/EQ1HKCYJM5U/default.jpg",
              "width": 120,
              "height": 90
             },
             "medium": {
              "url": "https://i.ytimg.com/vi/EQ1HKCYJM5U/mqdefault.jpg",
              "width": 320,
              "height": 180
             },
             "high": {
              "url": "https://i.ytimg.com/vi/EQ1HKCYJM5U/hqdefault.jpg",
              "width": 480,
              "height": 360
             }
            },
            "channelTitle": "BBC",
            "liveBroadcastContent": "none"
           }
          },
          {
           "kind": "youtube#searchResult",
           "etag": "XI7nbFXulYBIpL0ayR_gDh3eu1k/gndGQ3TuSgooLxMWqXUNH42n9Gs",
           "id": {
            "kind": "youtube#video",
            "videoId": "JMfPnJm-L1E"
           },
           "snippet": {
            "publishedAt": "2017-01-19T13:00:00.000Z",
            "channelId": "UChGJGhZ9SOOHvBB0Y4DOO_w",
            "title": "Amusement Park for Kids Rides! Meeting Disney Characters + Animal Kingdom Hotel + Toy Hunt Shopping",
            "description": "Amusement Park for Kids Rides at Disney World Part 3. We also meet Disney Characters like Goofy, Mickey Mouse, Winnie the Pooh and Friends like Piglet, ...",
            "thumbnails": {
             "default": {
              "url": "https://i.ytimg.com/vi/JMfPnJm-L1E/default.jpg",
              "width": 120,
              "height": 90
             },
             "medium": {
              "url": "https://i.ytimg.com/vi/JMfPnJm-L1E/mqdefault.jpg",
              "width": 320,
              "height": 180
             },
             "high": {
              "url": "https://i.ytimg.com/vi/JMfPnJm-L1E/hqdefault.jpg",
              "width": 480,
              "height": 360
             }
            },
            "channelTitle": "Ryan ToysReview",
            "liveBroadcastContent": "none"
           }
          },
          {
           "kind": "youtube#searchResult",
           "etag": "XI7nbFXulYBIpL0ayR_gDh3eu1k/2BOFfv8H3D1DNKegJ8_aj4HN_vc",
           "id": {
            "kind": "youtube#video",
            "videoId": "dW5plLrebUg"
           },
           "snippet": {
            "publishedAt": "2013-02-21T20:51:06.000Z",
            "channelId": "UCIxiXRZqUv9zYVM80cz6ZnA",
            "title": "Expedition Everest front seat on-ride HD POV Disney's Animal Kingdom",
            "description": "With incredible themeing & thrills galore, could this be Disney's best roller coaster? Taking six years to design & construct at an estimated total cost of $100 ...",
            "thumbnails": {
             "default": {
              "url": "https://i.ytimg.com/vi/dW5plLrebUg/default.jpg",
              "width": 120,
              "height": 90
             },
             "medium": {
              "url": "https://i.ytimg.com/vi/dW5plLrebUg/mqdefault.jpg",
              "width": 320,
              "height": 180
             },
             "high": {
              "url": "https://i.ytimg.com/vi/dW5plLrebUg/hqdefault.jpg",
              "width": 480,
              "height": 360
             }
            },
            "channelTitle": "CoasterForce",
            "liveBroadcastContent": "none"
           }
          }
         ]
        }
        """
        self.search_response = json.loads(self.search_response_json_string)

    def test_create_client_raises_error_on_missing_key(self):
        """Does create_client raise an error on missing key?"""
        empty_keys = json.dumps({"foo": "bar"})
        with patch('builtins.open', mock_open(read_data=empty_keys), create=True):
            self.assertRaises(KeyError, youtube_search.VideoCrawler.create_client)

    @patch("youtube_search.VideoCrawler.get_views")
    def test_parse_response_skips_item_with_views(self, mock_get_views):
        """Does parse_response skip items with > 0 views detected?"""
        mock_get_views.side_effect = [False, False, True]  # mark the last item as having > 0 views

        zero_views = self.crawler.parse_response(self.search_response)
        self.assertEqual(len(zero_views), 2)

    @patch("youtube_search.VideoCrawler.get_views")
    def test_parse_response_skips_live_broadcast_items(self, mock_get_views):
        """Does parse_response skip items with a liveBroadcastContent status?"""
        mock_get_views.side_effect = [False, False, False]
        self.search_response["items"][2]["snippet"]["liveBroadcastContent"] = "true"

        zero_views = self.crawler.parse_response(self.search_response)
        self.assertEqual(len(zero_views), 2)

    def test_search_parameter_formatting_without_date(self):
        """Does format_search_params return the expected data when called with the default
        value of None as the before date?
        """
        res = self.crawler.format_search_params("peppery")

        before = res["before"][:10]  # date part of the string
        before = datetime.datetime.strptime(before, "%Y-%m-%d")
        after = res["after"][:10]
        after = datetime.datetime.strptime(after, "%Y-%m-%d")

        delta = before - after
        self.assertEqual(res["q"], "peppery")
        self.assertEqual(delta.days, 180)

    def test_search_parameter_formatting_with_date(self):
        """Does format_search_params return the expected data when called with a before date?"""
        before = datetime.date(2015, 4, 16)
        res = self.crawler.format_search_params("peppery", before)

        before = res["before"][:10]  # date part of the string
        before = datetime.datetime.strptime(before, "%Y-%m-%d")
        after = res["after"][:10]
        after = datetime.datetime.strptime(after, "%Y-%m-%d")

        delta = before - after
        self.assertEqual(res["q"], "peppery")
        self.assertEqual(delta.days, 180)

    def test_randomized_date_range_is_valid(self):
        """Is the date created by choose_random_date between 1.1.2006 and year ago?"""
        random_date = self.crawler.choose_random_date()
        year_ago = datetime.date.today() - datetime.timedelta(days=365)
        start_date = datetime.date(2006, 1, 1)

        self.assertTrue(random_date <= year_ago)
        self.assertTrue(random_date >= start_date)

    def test_compute_earlier_date(self):
        """Does compute_earlier_date return a date corresponding to the parameters?."""
        start1 = datetime.date(2014, 10, 1)
        end1 = datetime.date(2014, 9, 21)
        res1 = self.crawler.compute_earlier_date(start1, 10)
        self.assertEqual(res1, end1)

        start2 = datetime.date(2017, 10, 30)
        end2 = datetime.date(2017, 5, 3)
        res2 = self.crawler.compute_earlier_date(start2, 180)
        self.assertEqual(res2, end2)

    def test_date_to_isoformat_properly_formats_date(self):
        """Is the string returned by date_to_isoformat a valid RFC 3339 string?"""
        today = datetime.date.today()
        formatted = self.crawler.date_to_isoformat(today)

        self.assertTrue(formatted.endswith("T00:00:00Z"))


if __name__ == "__main__":
    """Create test suites from both classes and run tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(VideoCrawlerTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
