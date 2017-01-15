#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
youtube_search.py

searches for YouTube videos with no views

The Google YouTube Data API comes with certain restrictions that prevents
from directly searching for content with no views. Namely: 
  1)  one cannot use view count as a search parameter, and 
  2)  any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
bunch of search terms and saves the results with zero views to a file.

The search terms are read from a dictionary file consisting of ~ 71 000
words. The script runs around a buffer based system: the words are read
in groups of 50, these are then queried against the YouTube API and valid
results are stored to file (links.pkl). The next runs of the script then
tweets the topmost result until the file is exhausted and the next 50 
search terms are processed for new results. 

Changelog:
11.1.2017
  * Refactoring: separated the bot feature to its own file. This file is now
    a somewhat more general purpose library module for searching for zero view item. 
  * Logging is now handled by the logging module.
8.1.2017
  * Fixed the -q switch, which has apparently been broken for quite a while...
  * Added a format_search_params() for formatting search parameters to the format required by
    youtube_query()
  * Minor code cleanup
8.8.2016
  * Querying: youtube_query() now checks whether the current page is empty
	and returns the last non-empty page
  * Querying: added common.txt as a source for common multi word search 
	terms
	* Querying: added option to use a random year long time window to
	  narrow done results.
		TODO: find out if this has any effect
	* Bot behavior: added a --parse switch to keep the tweet and parsing new
	  videos separate. The intended behavior is now to parse for a large
	  number of videos once a day and do nothing if links.json is empty
	* Code cleanup:
	  * moved from pickle to json and deleted the --show switch
	  * moved some stuff under main to functions for readability
	  * command line arguments are now properly parsed before calling
		main()

3.4.2016
  * Querying: changed paginitaion in youtube_query() to use the API's
	list_next() method
  * Parsing: zero_search() now parses more than one results per search term
	(by default, all items in the last page of the results)
  * Parsing: search results with liveContent == "upcoming" are now
	considered invalid (results to "upcoming" videos that have already
	occured and can no longer be viewed, maybe find out why this
	is happening?)
  * Maintenance: added an --empty switch for emptying links.pkl

25.2.2016
  * I/O: output is now stored as pickle encoded dicts (links.pkl)
	instead of a raw csv text file.
  * I/O: added a dynamic index file (search_terms.pkl) to keep track of
	which words to read next, no more cumbersome byte index method.
  * Code cleanup: the zero search part is now down to 1 function,
	(zero_search()) and the bot feature is moved directly under main()

16.1.2016
  * Code cleanup: added publishedBefore argument to
	youtube.search().list()

12.9.2015
  * Initial release
"""
 

import json
import random
import argparse
import datetime
import logging
import os.path

from apiclient.discovery import build
from apiclient.errors import HttpError



class YoutubeParser:

  def __init__(self):
    """Define path to the working folder where datafiles are stored, setup a logger and create a youtube object.
    to interact with the API.
    """
    self.path = "./"  # path to where external files (keys.json, dict.txt, common.txt) are stored
    # Create a logger and attach a formatter and a file handler to it.
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    self.logger = logging.getLogger()
    self.logger.setLevel(logging.INFO)

    # Attach a FileHandler to point output to serach.log
    file_handler = logging.FileHandler(self.path + "search.log")
    file_handler.setFormatter(log_formatter)
    self.logger.addHandler(file_handler)

    # ...and a StreamHandler to also send output to stderr
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    self.logger.addHandler(console_handler)

    # Create an object to interact with the YouTube API.
    with open(self.path + "keys.json") as f:
      keys = json.load(f)

    # Set API key to the key at APIs & auth > Registered apps tab of
    # https://cloud.google.com/console
    GOOGLE_API_KEY = keys["GOOGLE_API_KEY"]
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey = GOOGLE_API_KEY)

    # Create a search term index if it doesn't exist.
    if not os.path.isfile(self.path + "links.json"):
      self.create_index()


  #========================================================================================
  # Youtube query functions =
  #==========================
  def youtube_query(self, search_params):
    """Perform a single YouTube query using given search parameters. Order results by viewcount and
    return the final page of the result set.
    Arg:
      search_params (dict): a dict of {q, publishedBefore, publishedAfter} arguments to be passed to
      youtube.search().list()
    Return:
      the final page of the results as dicts of items returned by YouTube API
      or None if no results.
    """
    request = self.youtube.search().list(
      q = search_params["q"],
      part = "id,snippet",
      publishedBefore = search_params["before"],
      publishedAfter = search_params["after"],
      relevanceLanguage = "en",
      maxResults = 50,
      order = "viewCount",
      type = "video"
    )

    # Call list_next() until no more pages to fetch or no items in current page.
    response = None
    while request is not None:
      prev_response = response
      response = request.execute()
      request = self.youtube.search().list_next(request, response)

      # If the current response doesn't contain any items,
      # return the previous response (possibly None).
      if not response["items"]:
        return prev_response

    return response


  def zero_search(self, n = 100, random_window = False):
    """Perform youtube_query() on n serach terms with:
      -n/2 items read from the top of search_terms.json, and
      -n/2 items read generated randomly by combining words in common.txt.
    Check for videos with no views and return as a list.
    Args:
      n (int): total number of search queries to perform
      random_window (boolean): whether a year long time window should be randomly generated
        as an additional search parameter. If False, the search window will be set to match
        any videos published at least a year ago from today
    Return:
      a list of {title, url, views, published} dictionaries
    """
    with open(self.path + "search_terms.json", "r") as f:
      search_terms = json.load(f)

    # Init a list for detected zero view items.
    zero_views = [] 

    # Get the first n/2 search terms from search_terms.json.
    next_slice = search_terms[:n/2]
    working_set = next_slice
    tail = search_terms[n/2 + 1:]

    # Generate another n/2 search terms from common.txt.
    for i in range(n/2):
      term = self.random_search_term(2)
      working_set.append(term)

    # Store the rest of the search term index back to file or re-initialize it
    # if there is nothing left to store.
    if tail:
      with open(self.path + "search_terms.json", "w") as f:
        json.dump(tail, f)
    else:
      print "Index empty, re-initializing..."
      self.create_index()

    # Format a dict of {q, before, after} for search parameters.
    search_params = self.format_search_params("", random_window)

    # Call youtube_query
    for search_term in working_set:
      search_term = search_term.encode("utf8") # encode as utf8 for sending data to the API
      search_params["q"] = search_term
      try:
       response = self.youtube_query(search_params)
      # TODO: better error handling, use the logging module?
      except UnicodeEncodeError as e:
        self.logger.error(e)

      # If no results, skip to next search_term.
      if response is None:
        continue

      # Loop through items in the last page.
      #print search_term
      found = False
      items = response["items"]
      for item in reversed(items):
        vid_id = item["id"]["videoId"]
        stats = self.get_stats(vid_id)
        views = int(stats["views"])
        live = item["snippet"]["liveBroadcastContent"]
        url = "https://www.youtube.com/watch?v=" + vid_id

        # Check for no view items not having live content (past events with live content will link to a "content not available" video).
        # items is reversed: if the current item has views, skip to the next search term.
        if views:
          break

        if live == "none":
          title = item["snippet"]["title"]
          view_count = stats["views"]
          upload_date = stats["upload_date"]

          # Add a new entry to zero_views.
          data = {"title": title, "url": url, "views": view_count, "date": upload_date}
          zero_views.append(data)
          found = True

        # No views, but has live content: print for logging purposes.
        else:
          self.logger.info("liveBroadcastContent: %s", live)

      # Print a checkmark if this search term provided at least one result.
      if found:
        print search_term + " ✓"
      else:
        print search_term


    self.logger.info("%s new links detected", len(zero_views))
    return zero_views



  #==============================================================================
  # Helper functions =
  #===================
  def create_index(self):
    """Read dict.txt to a dynamic json index file."""
    with open(self.path + "dict.txt") as f:
      search_terms = f.read().splitlines()

    with open(self.path + "search_terms.json", "w") as f:
      json.dump(search_terms, f)


  def get_stats(self, vid_id):
    """Get view count and upload date for the given video.
    Arg:
      vid_id (string): a Youtube video id
    Return:
      a dict of the view count and upload date
    """
    stats = self.youtube.videos().list(
      part = "statistics,snippet",
      id = vid_id
    ).execute()

    viewcount = stats["items"][0]["statistics"]["viewCount"]
    date = stats["items"][0]["snippet"]["publishedAt"]

    # date is in ISO format (YYYY-MM-DD), reformat to DD.MM.YYYY 
    d = date[8:10]
    m = date[5:7]
    y = date[0:4]
    date = d + "." + m + "." + y

    return { "views": viewcount, "upload_date": date }


  def random_search_term(self, nword = 1):
    """Generate a random search term from common.txt.
    Arg:
      nword (int): number of words the returned search term should consist of
    Return:
      the search term
    """
    # Combine two or more common words for long search term.
    with open(self.path + "common.txt") as f:
      lines = [line.rstrip("\n") for line in f]
      rand = random.sample(lines, nword)
      rand = " ".join(rand)

    return rand


  def randomize_window(self):
    """Create random RFC 3339 timestamps for a period of one year between a year ago and 1.1.2006,
    Yotube was founded on 14.2.2005.
    Return:
      a dict of "start" and "end" values
    """
    # Compute how many days between today and 1.1.2006.
    delta = datetime.date.today() - datetime.date(2006, 1, 1)
    delta = delta.days

    # Randomly choose a day delta between [365, delta] and create a timestap
    # for the end date.
    delta = random.randint(365, delta)
    d = datetime.datetime.utcnow()
    d = d - datetime.timedelta(days = delta)
    end = d.isoformat("T") + "Z"

    # Timestamp for year earlier for start.
    d = d - datetime.timedelta(days = 365)
    start = d.isoformat("T") + "Z"

    return {"start": start, "end":end}


  def format_search_params(self, q, random_window = False):
    """Format a dict of query parameters to pass
    to youtube_query().
    Args:
      q (string): the search term to use
      random_window: (boolean): whether a randomized timewindow should be generated.
    Return:
      a dict of {q, before, after}
    """
    search_params = {"q": q, "before": None, "after": None}
    if random_window:
      window = self.randomize_window()
      search_params["before"] = window["end"]
      search_params["after"] = window["start"]
      print "Using timewindow: {} - {}".format(window["start"], window["end"])

    else:
      before = datetime.datetime.utcnow() - datetime.timedelta(days = 365)
      search_params["before"] = before.isoformat("T") + "Z"

    return search_params


  #==============================================================================
  # Main =
  #=======
  def main(self, args):
    """Define procedures for each command line argument.
    TODO: Should this script even be runnable?
    Arg:
      args (list): a list of command line arguments passed to the script
    """

    # -q
    # Perform a sample search and  show results on stdout. Doesn't modify
    # links.json or search_terms.json, but doen't guarantee zero view items either.
    if args.q:
      search_params = self.format_search_params(args.q, args.random_window)  # format a dict of parameters as required by youtube_query()
      response = self.youtube_query(search_params)
      if not response:
        print "No results"
      
      else:
        # Get all items from the last page of results.
        for res in response["items"]:
          vid_id = res["id"]["videoId"]
          stats = self.get_stats(vid_id)
          views = int(stats["views"])

          title = res["snippet"]["title"]
          url = "https://www.youtube.com/watch?v=" + vid_id
          view_count = stats["views"]
          upload_date = stats["upload_date"]
          print title
          print url
          print "views:", views
          print "uploaded:", upload_date



#==============================================================================
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("-q", help = "Perform a sample search on given search term. Prints the items with least views to stdout.", metavar = "search_term")
  parser.add_argument("--random-window", help = "Whether a randomized year long time window should be used with the -q switch.", action="store_true")
  args = parser.parse_args()
  #print args

  
  try:
    app = YoutubeParser()
    app.main(args)
    print "Note: this module is mainly intended as a library module for twitterbot.py. Run python 'twitterbot.py --parse' to see it in proper action."
  except HttpError as e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
  except IOError as e:
    print e
    print "Try initialiazing this script with the --init switch"
  


  





