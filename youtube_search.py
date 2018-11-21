#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
youtube_search.py

Library module for searching YouTube videos with no views.

The Google YouTube Data API comes with certain restrictions that prevents
from directly searching for content with no views. Namely:
  1) view count cannot be used as a search parameter, and
  2) any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
number of search terms and keeps track of the results with zero views.

The search terms are read from a text file containing common English language
words. To prevent the same search term from returning the same results, a random timeframe
is generated for each API query.
"""

import json
import random
import datetime
import tqdm

from apiclient.discovery import build


class VideoCrawler(object):
    """Looks for videos with no views."""

    def __init__(self, search_terms=None):
        self.search_terms = search_terms
        self.n = 0
        self.client = VideoCrawler.create_client()

    def run(self, n):
        """Main entrypoint to the crawler. Generate a list of search terms and
        run the search over them.
        """
        self.search_terms = self.generate_search_terms(n)
        self.n = n
        links = self.zero_search(self.search_terms)

        for link in links:
            print(link.title)
            print(link.channel)
            print(link.url)
            print(link.publish_date)
            print()

    @staticmethod
    def create_client():
        """Create a youtube client."""
        with open("./keys.json") as f:
            data = json.load(f)

        try:
            GOOGLE_API_KEY = data["GOOGLE_API_KEY"]
            YOUTUBE_API_SERVICE_NAME = "youtube"
            YOUTUBE_API_VERSION = "v3"
            client = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                           developerKey=GOOGLE_API_KEY)
        except KeyError:
            raise KeyError("Missing Google API key in keys.json")

        return client

    def zero_search(self, search_terms):
        """Look for videos with no views. Perform a search on a list of search terms and
        record items with no views.
        Args:
          search_terms (list): a list of search terms to perform the query
        Return:
          a list of VideoResult instances build from the items with no response.
        """
        zero_views = []

        # Perform a youtube query for each search term.
        # need total steps for bar to update when used with a generator
        for search_term in tqdm.tqdm(search_terms, total=self.n):
            # print the search term and a return carriage without a newline
            tqdm.tqdm.write(search_term, end="\r"),

            query_params = self.format_search_params(search_term)
            response = self.query_youtube(**query_params)
            if response:
                video_results = self.parse_response(response)
                if video_results:
                    # write a checkmark to denote a succesful search
                    tqdm.tqdm.write(search_term + " ✓")  # rewrite search term with a checkmark
                    zero_views.extend(video_results)

        return zero_views

    def query_youtube(self, **kwargs):
        """Perform a YouTube query on a single search term provided via parameter. Order results by viewcount and
        return the final page of the result set.
        Arg:
          kwargs: parameters to pass to youtube.search().list()
        Return:
          the final page of the results as dicts of items returned by YouTube API
          or None if no results.
        """
        request = self.client.search().list(
            q=kwargs["q"],
            part="id,snippet",
            publishedBefore=kwargs["before"],
            publishedAfter=kwargs["after"],
            relevanceLanguage="en",
            maxResults=50,
            order="viewCount",
            type="video"
        )

        # fetch the next response page until no more pages or no items in current page.
        response = None
        while request is not None:
            prev_response = response
            response = request.execute()
            try:
                request = self.client.search().list_next(request, response)
            except UnicodeEncodeError:  # TODO: find out what's going on here
                with open("./list_next_error.json", "w") as f:
                    json.dump(response, f, indent=2, separators=(',', ': '))
                print(request)
                print(response)
                return None

            # If the current response doesn't contain any items,
            # return the previous response (possibly None).
            if not response["items"]:
                return prev_response

        return response

    def parse_response(self, response):
        """Parse a response page from the API for videos with no views.
        Arg:
          response (dict): the API response to a search query
        Return:
          a list of VideoResult instances build from the items with no response.
        """
        valid = []
        for item in reversed(response["items"]):  # loop backwards so item with least views is first
            vid_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            publish_date = item["snippet"]["publishedAt"]
            channel_title = item["snippet"]["channelTitle"]
            url = "https://www.youtube.com/watch?v={}".format(vid_id)

            views = self.get_views(vid_id)

            # return as soon as we find a video which has views
            if views:
                return valid

            # skip videos with live broadcast content: these often lead to missing videos with a "content not available" notification
            live = item["snippet"]["liveBroadcastContent"]
            if live == "none":
                link = VideoResult(title=title, channel=channel_title, url=url,
                                   views=views, publish_date=publish_date)
                valid.append(link)

        return valid

    def get_views(self, vid_id):
        """Get view count for a given video from the API.
        Arg:
          vid_id (string): a Youtube video id
        Return:
          a dict of the view count and upload date
        """
        stats = self.client.videos().list(
            part="statistics",
            id=vid_id
        ).execute()

        # View count is not always among the response, ignore these by manaully
        # settings a high view count value.
        try:
            viewcount = int(stats["items"][0]["statistics"]["viewCount"])
        except KeyError:
            viewcount = 100

        return viewcount

    def generate_search_terms(self, n):
        """A generator function for generating random search terms from common.txt
        Arg:
          n (int): number of search terms to generate
        Return:
          a list of search terms
        """
        with open("./common.txt") as f:
            lines = [line.rstrip("\n") for line in f]

        sample = random.sample(lines, n)
        return sample

    def format_search_params(self, q, before=None):
        """Format a dict of query parameters to pass to the youtube query API. The parameters include
        the search term and the 'before' and 'after' values. 'after' is set to a year backwards from 'before' while
        'before' is either given as a parameter or randomly set to somewhere between a year ago and 1.1.2006.
        Args:
          q (string): the search term to use
          before (date): a date object. If not set, a random timestamp from at least a year ago will be generated.
        Return:
          a dict of {q, before, after}
        """
        # if a date argument was provided, generate a starting point from year earlier
        # TODO input validation
        if before:
            after = self.compute_earlier_date(before, 180)

        # generate a timewindow
        else:
            before = self.choose_random_date()
            after = self.compute_earlier_date(before, 180)

        iso_before = self.date_to_isoformat(before)
        iso_after = self.date_to_isoformat(after)
        search_params = {"q": q, "before": iso_before, "after": iso_after}

        return search_params

    def choose_random_date(self):
        """Randomly choose a date between a year ago and 1.1.2006, (Yotube was founded on 14.2.2005).
        Return:
          a date object
        """
        # compute number of days since 1.1.2006
        delta = datetime.date.today() - datetime.date(2006, 1, 1)
        delta = delta.days

        # Randomly choose a day offset from 1.1.2006
        offset = random.randint(0, delta - 365)
        random_date = datetime.date(2006, 1, 1) + datetime.timedelta(days=offset)
        return random_date

    def compute_earlier_date(self, start, days):
        """Given a date and a number of days, compute the date matchin which occured
        that many days eralier.
        Args:
            start (date): a date object
            days (int): number of days earlier the output date should be
        Return:
          a datetime
        """
        return start - datetime.timedelta(days=days)

    def date_to_isoformat(self, date):
        """Format a date object as RFC 3339 timestamp with 0s as time values.
        Arg:
            date (date): a date object
        Return:
          a formatted string
        """
        return date.isoformat() + "T00:00:00Z"


class VideoResult(object):
    """A wrapper for detected zero view items."""

    def __init__(self, title, url, views, publish_date, channel=None):
        self.title = title
        self.channel = channel
        self.url = url
        self.views = views
        self.publish_date = publish_date

    def __repr__(self):
        return "Title: {}, Channel: {}, url: {} views: {} publish_date: {}".format(
            self.title,
            self.channel,
            self.url,
            self.views,
            self.publish_date
        )
