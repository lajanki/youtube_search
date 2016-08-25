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
 

import time
import json
import random
import twython
import argparse
import datetime

from apiclient.discovery import build
from apiclient.errors import HttpError



rpi_path = "/home/pi/python/youtube_search/"

# Get required Twitter and Google keys from file.
with open(rpi_path + "keys.json") as f:
  keys = json.load(f)

# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = keys["GOOGLE_DEVELOPER_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey = DEVELOPER_KEY)


#========================================================================================
# Bot functions =
#================
def init_bot(start = None):
  """Read contents of dict.txt and store it as a working file in search_terms.json,
  from which they will be deleted once processed.
  Arg:
    start (string): the search term to start building the index. Should be one of the
    search terms in dict.txt.
  Modifies:
    search_terms.json: file for search terms to use
    links.json: links for valid videos found
  """
  # read dict.txt to a list split by newlines
  with open(rpi_path + "dict.txt", "r") as f:
    search_terms = f.read().splitlines() 

  if start:
    try:
      idx = search_terms.index(start)
      search_terms = search_terms[idx:]
    except ValueError as e:
      print e
      print "Using the full index."

  # overwrite previous search_terms.json
  with open(rpi_path + "search_terms.json", "w") as f:
    json.dump(search_terms, f)

  # init an empty links.json
  with open(rpi_path + "links.json", "w") as f:
    json.dump([], f)


def tweet():
  """tweet the top item from links.json or do nothing if empty."""
  with open(rpi_path + "links.json", "r") as f:
    link_data = json.load(f)

  #print time.strftime("%d.%m.%Y %H:%M:%S")
  # 1 check if there is something to tweet
  if link_data:
    link = link_data.pop(0) 

    # format the tweet
    msg = link["title"] + "\n" + link["link"] + "\n" + "uploaded: " + link["date"] + "\n" + "views: " + link["views"]
    surplus = len(msg) - 140

    # if tweet too long, cut title
    if surplus:
      msg = link["title"][:-surplus] + "\n" + link["link"] + "\n" + "uploaded: " + link["date"] + "\n" + "views: " + link["views"]
      print "Title cut to keep tweet within 140 characters."

    API_KEY = keys["API_KEY"]
    API_SECRET = keys["API_SECRET"]
    OAUTH_TOKEN = keys["OAUTH_TOKEN"]
    OAUTH_SECRET = keys["OAUTH_SECRET"]
    twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
    twitter.update_status(status = msg)
    print "Latest tweet:"
    print msg
      
    # write the rest of link_data back to file
    with open(rpi_path + "links.json", "w") as f:
        json.dump(link_data, f)

  # nothing to tweet
  else:
    print "links.json in empty"


#========================================================================================
# Youtube query functions =
#==========================
def youtube_query(search_params):
  """Query YouTube using search_term. Order results by viewcount and
  return the final page of results.
  Arg:
    search_params (dict): a dict of q, publishedBefore and publishedAfter arguments to be passed to
    youtube.search().list()
  Return:
    the final page of the results as dicts of items returned by YouTube API
    or None if no results
  """
  request = youtube.search().list(
    q = search_params["q"],
    part = "id,snippet",
    publishedBefore = search_params["before"],
    publishedAfter = search_params["after"],
    relevanceLanguage = "en",
    maxResults = 50,
    order = "viewCount",
    type = "video"
  )

  # call list_next() until no more pages to fetch or no items in current page
  response = None
  while request is not None:
    prev_response = response
    response = request.execute()
    request = youtube.search().list_next(request, response)

    # if the current response doesn't contain any items,
    # return the previous response (may be None)
    if not response["items"]:
      #print "empty page, returning previous page"
      return prev_response

  return response


def zero_search(n = 200, last_only = False, random_window = False):
  """Query YouTube on search terms read from search_terms.json and common.txt
  and parse them for zero view videos. Store results to
  links.json. Search terms are read evenly from both input sources.
  Args:
    n (int): total number of search terms to read
    last_only (boolean): whether only the last item (==least views) of the YouTube query
      results should be processed
    random_window (boolean): whether a year long time window should be randomly generated
      for querying YouTube
  """
  with open(rpi_path + "search_terms.json", "r") as f:
    search_terms = json.load(f)

  # init a list for zero view items
  valid = [] 

  # get the first n/2 search terms from file
  next_slice = search_terms[:n/2]
  working_set = next_slice
  tail = search_terms[n/2 + 1:]

  # pick another n/2 search terms randomly from common.txt
  # using random_search_term()
  for i in range(n/2):
    term = random_search_term(2)
    working_set.append(term)

  # define search parameters: search term, after and before
  search_params = {"q":None, "before":None, "after":None}
  # use random time window
  if random_window:
    window = randomize_window()
    search_params["before"] = window["end"]
    search_params["after"] = window["start"]
    print "Using timewindow: {} - {}".format(window["start"], window["end"])

  # set before to year ago and keep after as None
  else:
    before = datetime.datetime.utcnow() - datetime.timedelta(days = 365)
    search_params["before"] = before.isoformat("T") + "Z"

  # call youtube_query to get the page containing
  # the least viewed search results
  for search_term in working_set:
    search_params["q"] = search_term
    response = youtube_query(search_params)

    # if no results, skip to next search_term
    if response is None:
      continue

    # loop through items in the last page
    print search_term

    items = response["items"]
    if last_only:
      items = items[-1:]  # last item as a list
    for item in reversed(items):
      vid_id = item["id"]["videoId"]
      stats = get_stats(vid_id)
      views = int(stats["views"])
      live = item["snippet"]["liveBroadcastContent"]

      # check for no view items not having live content.
      # items is reversed: if the current item has views, the rest can be skipped
      if views:
        break

      elif live == "none":
        title = item["snippet"]["title"]
        link = "https://www.youtube.com/watch?v=" + vid_id
        view_count = stats["views"]
        upload_date = stats["upload_date"]
        print title
        print link

        # add info as a tuple to valid
        data = {"title": title, "link": link, "views": view_count, "date": upload_date}
        valid.append(data)

      # no views, but has live content: print for logging purposes
      else:
        print "liveBroadcastContent: ", live
        print link


  # add valid to file, don't overwrite previous
  with open(rpi_path + "links.json") as f:
    old = json.load(f)

  # reopen in w mode to overwite previous data
  with open(rpi_path + "links.json", "w") as f:
    valid.extend(old)
    json.dump(valid, f)

  # store the rest of the index back to file or re-initialize it
  # if nothing to store
  if tail:
    with open(rpi_path + "search_terms.json", "w") as f:
      json.dump(tail, f)
  else:
    print "Index empty, re-initializing..."
    init_bot()


#==============================================================================
# Helper functions =
#===================
def get_stats(vid_id):
  """Get view count and upload date for the given video.
  Arg:
    vid_id (string): a Youtube video id
  Return:
    a dict of the view count and upload date
  """
  stats = youtube.videos().list(
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


def random_search_term(nword = 1):
  """Get a random search term from dict.txt.
  Arg:
    nword (int): number of words the returned search term should consist of
  Return:
    the search term
  """
  # combine two or more common words for long search term
  if nword > 1:
    with open(rpi_path + "common.txt") as f:
      lines = [line.rstrip("\n") for line in f]
      rand = random.sample(lines, nword)
      rand = " ".join(rand)

  # use dict.txt for single word search terms
  else:
    with open(rpi_path + "dict.txt") as f:
      lines = [line.rstrip("\n") for line in f]
      rand = random.choice(lines)

  return rand


def randomize_window():
  """Create random RFC 3339 timestamps for a period of one year between a year ago and 1.1.2006,
  Yotube was founded on 14.2.2005.
  Return:
    a dict of "start" and "end" values
  """
  # compute how many days between today and 1.1.2006
  delta = datetime.date.today() - datetime.date(2006, 1, 1)
  delta = delta.days

  # randomly choose a day delta between [365, delta] and create a timestap
  # for the end date
  delta = random.randint(365, delta)
  d = datetime.datetime.utcnow()
  d = d - datetime.timedelta(days = delta)
  end = d.isoformat("T") + "Z"

  # timestamp for year earlier for start
  d = d - datetime.timedelta(days = 365)
  start = d.isoformat("T") + "Z"

  return {"start": start, "end":end}



#==============================================================================
# Main =
#=======
def main(args):
  """Define procedures for each argument."""

  # --init
  # initialize search_terms.json
  if args.init:
    if isinstance(args.init, str):
      print "Initializing index starting from " + args.init + "..."
      init_bot(args.init)
    else:
      print "Initializing..."
      init_bot()


  # --empty
  # initialize links.json
  elif args.empty:
    with open("links.json", "w") as f:
      json.dump([], f)


  # --tweet
  # attempt to tweet the top item in links.json
  elif args.tweet:
    tweet()
    print "\n"


  # --parse
  # store new links to file and measure execution time.
  # Only parse new links if < 10 items currently stored
  elif args.parse:
    with open(rpi_path + "links.json") as f:
      links = json.load(f)

    if len(links) < 10:
      print "Parsing for new links..."
      start = time.time()
      zero_search(n = args.parse, random_window = args.random_window)
      time_ = round(time.time() - start)
      time_ = datetime.timedelta(seconds = time_)
      print "Finished in {}".format(time_)

    else:
      print "No action,", len(links), "links left in links.json"
    print "\n"


  # -q
  # sample search to console, does not guarentee a zero view item
  elif args.q:
    response = youtube_query(args.q, random_window = args.random_window)

    if response is None:
      print "No results"
    
    else:
      # get all items from the last page of results
      for res in response["items"]:
        vid_id = res["id"]["videoId"]
        stats = get_stats(vid_id)
        views = int(stats["views"])

        title = res["snippet"]["title"]
        link = "https://www.youtube.com/watch?v=" + vid_id
        view_count = stats["views"]
        upload_date = stats["upload_date"]
        print title
        print link
        print "views:", views
        print "uploaded:", upload_date


  # no argument provided, show usage
  else:
    parser.print_help()



#==============================================================================
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("-q", help = "Perform a sample search on given search term. Returns the item with least views.", metavar = "search term")
  parser.add_argument("--tweet", help = "Tweet the next result from links.dat", action = "store_true")
  parser.add_argument("--init", help = """Initialize an empty set of links and create a search index by reading dict.txt.
    An optional argument matching a search term in dict.txt can be provided to mark the starting point of the index.""",
    nargs = "?", const = True, metavar = "search term")
  parser.add_argument("--parse", help = "Parse n next search terms for zero view items and store to links.json.", metavar = "n", type = int)
  parser.add_argument("--empty", help = "Soft initialization: empty links.json but keep the index intact.", action = "store_true")
  parser.add_argument("--random-window", help = """Whether a randmized, year long, time window should be used when
    querying YouTube. Affects -q and --parse switches.""", action = "store_true")
  args = parser.parse_args()
  #print args

  try:
    main(args)
  except HttpError as e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
  except IOError as e:
    print e
    print "Try initialiazing this script with the --init switch"


  





