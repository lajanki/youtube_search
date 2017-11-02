#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os
import datetime


# change working directory for relative paths in youtube_search to work as well as
# to be able to import the main module
os.chdir("..")
import youtube_search


class VideoBrowserTestCase(unittest.TestCase):
	"""Does the browser work correctly?"""

	@classmethod
	def setUpClass(self):
		self.browser = youtube_search.VideoBrowser()

	def testStatValueTypes(self):
		"""Does get_stats return a dict with correct types?"""
		vid_id = "YjkwdEXoeZI"
		stats = self.browser.get_stats(vid_id)
		self.assertIsInstance(stats["views"], int)
		self.assertIsInstance(stats["upload_date"], unicode)

	def testStatDateFormat(self):
		"""Is the upload_date in the stats of the form DD.MM.YYYY?"""
		vid_id = "YjkwdEXoeZI"
		stats = self.browser.get_stats(vid_id)

		upload_date = stats["upload_date"]
		split = upload_date.split(".")
		self.assertEqual(len(split), 3)

		self.assertEqual(len(split[0]), 2)
		self.assertEqual(len(split[1]), 2)
		self.assertEqual(len(split[2]), 4)

	def testQueryReturnsNoneIfNoResults(self):
		"""Is the response to a YouTube None for nonsense query?"""
		before = "2011-08-30T00:00:00Z"
		after = "2011-08-30T00:00:00Z"
		q = "SomeWeirdAndLongCamelCasedQueryStringThatProbablyDoesntReturnAnythingSuperInteresting.TheresProbablyABetterWayToTestThingsLikeThis.Mocks?"
		response = self.browser.query_youtube(q=q, before=before, after=after)
		self.assertIs(response, None, "Received an actual response to a nonsense query")

	def testQueryContainsItemsKey(self):
		"""Is there an "items" key in the response."""
		before = "2017-08-30T00:00:00Z"
		after = "2011-08-30T00:00:00Z"
		q = "best"
		response = self.browser.query_youtube(q=q, before=before, after=after)
		self.assertIn("items", response.keys(), "Response doesn't contain 'items' as key")


class VideoCrawlerTestCase(unittest.TestCase):
	"""Test cases for crawling videos."""

	@classmethod
	def setUpClass(self):
		self.crawler = youtube_search.VideoCrawler()

	def testSearchParamFormattingWithoutDate(self):
		"""Does format_search_params return the expected data when called with the default
		value of None as the before date?
		"""
		q = "peppery"
		res = self.crawler.format_search_params(q)

		before = res["before"][:10]  # date part of the string
		before = datetime.datetime.strptime(before, "%Y-%m-%d")
		after = res["after"][:10]
		after = datetime.datetime.strptime(after, "%Y-%m-%d")

		delta = before - after
		self.assertEqual(res["q"], q, "Unexpected query term")
		self.assertEqual(delta.days, 365, "Unexpected difference between dates")

	def testSearchParamFormattingWithtDate(self):
		"""Does format_search_params return the expected data when called with a before date?"""
		q = "peppery"
		before = datetime.date(2015, 4, 16)
		res = self.crawler.format_search_params(q, before)

		before = res["before"][:10]  # date part of the string
		before = datetime.datetime.strptime(before, "%Y-%m-%d")
		after = res["after"][:10]
		after = datetime.datetime.strptime(after, "%Y-%m-%d")

		delta = before - after
		self.assertEqual(res["q"], q, "Unexpected query term not")
		self.assertEqual(delta.days, 365, "Unexpected difference between dates")


class DateCreationTestCase(unittest.TestCase):
	"""Test cases for date creation functions."""

	@classmethod
	def setUpClass(self):
		self.crawler = youtube_search.VideoCrawler()

	def testRandomizedDateRangeValid(self):
		"""Is the date created by choose_random_date between 1.1.2006 and year ago?"""
		random_date = self.crawler.choose_random_date()
		year_ago = datetime.date.today() - datetime.timedelta(days = 365)
		after = datetime.date(2006, 1, 1)

		self.assertTrue(random_date <= year_ago, "randomized date is less than a year_ago")
		self.assertTrue(random_date >= after, "randomized date is before 1.1.2006")

	def testRandomizedDateIsADate(self):
		"""Does choose_random_date return a date object?"""
		random_date = self.crawler.choose_random_date()
		self.assertIsInstance(random_date, datetime.date, "choose_random_date returns an invalid type")

	def testYearSinceIsYearAgo(self):
		"""Does year_since return a date 365 before a given date."""
		today = datetime.date.today()
		year_ago = self.crawler.year_since(today)

		delta = today - year_ago
		self.assertEqual(delta.days, 365, "year_since is not 365 days before a date")

	def testDateToISOFormatIsProperlyFormatted(self):
		"""Is the string returned by date_to_isoformat a valid RFC 3339 string?"""
		today = datetime.date.today()
		formatted = self.crawler.date_to_isoformat(today)

		self.assertTrue(formatted.endswith("T00:00:00Z"), "returned date is not RFC 3339 formatted")
