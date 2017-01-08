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
 

import time
import json
import random
import twython
import argparse
import datetime

from apiclient.discovery import build
from apiclient.errors import HttpError



rpi_path = "./"  # path to the working folder (ie. where this script is located)

# Get required Twitter and Google keys from file.
with open(rpi_path + "keys.json") as f:
  keys = json.load(f)

# Set API key to the key at APIs & auth > Registered apps tab of
# https://cloud.google.com/console
GOOGLE_API_KEY = keys["GOOGLE_API_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey = GOOGLE_API_KEY)


#========================================================================================
# Bot functions =
#================
def init_bot(start = None):
  """Initializes the bot by parsing the contents of dict.txt as a dynamic index of search terms
  in search_terms.json, from which search terms will be deleted once processed. Also
  initializes a links.json file for detected items with no views.
  Arg:
    start (string): the search term to start building the index. Should be one of the
    search terms in dict.txt.
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

  with open(rpi_path + "search_terms.json", "w") as f:
    json.dump(search_terms, f)

  # Init an empty list for links.json.
  with open(rpi_path + "links.json", "w") as f:
    json.dump([], f)


def tweet():
  """Attempts to tweets the topmost item from links.json."""
  with open(rpi_path + "links.json", "r") as f:
    link_data = json.load(f)

  #print time.strftime("%d.%m.%Y %H:%M:%S")
  # Check if there actually is something to tweet
  if link_data:
    link = link_data.pop(0)
    url = link["link"]

    # Format the tweet message:
    # for long tweets, cut the title to 75 characters
    # url = 23 characters (after Twitter's own shortening, see https://support.twitter.com/articles/78124)
    # date = 20
    # views ~ 8
    # linebreaks = 3
    # => title: first 70 characters + ...
    if len(link["title"]) > 75:
      title = link["title"][:72] + "..."
      print "Title cut to keep tweet within 140 characters."
    else:
      title = link["title"]

    msg = title + "\n" + url + "\n" + "uploaded: " + link["date"] + "\n" + "views: " + link["views"]

    # Encode to uft8 for printing and sending to Twitter.
    msg = msg.encode("utf8")

    API_KEY = keys["TWITTER_API_KEY"]
    API_SECRET = keys["TWITTER_API_SECRET"]
    OAUTH_TOKEN = keys["TWITTER_OAUTH_TOKEN"]
    OAUTH_SECRET = keys["TWITTER_OAUTH_SECRET"]
    twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
    try:
      twitter.update_status(status = msg)
    except twython.exceptions.TwythonError as e:
      print e
      print "Attempted to tweet:"
      print msg
      print "Length:", len(msg)

    print "Latest tweet:"
    print msg
      
    # Write the rest of link_data back to file.
    with open(rpi_path + "links.json", "w") as f:
        json.dump(link_data, f)

  # There was nothing to tweet.
  else:
    print "links.json in empty"


#========================================================================================
# Youtube query functions =
#==========================
def youtube_query(search_params):
  """Perform a single YouTube query using search_term as a search term. Order results by viewcount and
  return the final page of results.
  Arg:
    search_params (dict): a dict of {q, publishedBefore, publishedAfter} arguments to be passed to
    youtube.search().list()
  Return:
    the final page of the results as dicts of items returned by YouTube API
    or None if no results.
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

  # Call list_next() until no more pages to fetch or no items in current page.
  response = None
  while request is not None:
    prev_response = response
    response = request.execute()
    request = youtube.search().list_next(request, response)

    # If the current response doesn't contain any items,
    # return the previous response (possibly None).
    if not response["items"]:
      #print "empty page, returning previous page"
      return prev_response

  return response


def zero_search(n = 200, last_only = False, random_window = False):
  """Perform a YouTube query using search terms read from search_terms.json and common.txt
  and parse them for zero view videos. Store results to
  links.json. Search terms are read evenly from both input sources.
  Args:
    n (int): total number of search terms to read
    last_only (boolean): whether only the last item (==least views) of the YouTube query
      results should be processed
    random_window (boolean): whether a year long time window should be randomly generated
      as an additional search parameter. If False, the search window will be
      before a year ago from today.
  """
  with open(rpi_path + "search_terms.json", "r") as f:
    search_terms = json.load(f)

  # Init a list for detected zero view items.
  valid = [] 

  # Get the first n/2 search terms from search_terms.json.
  next_slice = search_terms[:n/2]
  working_set = next_slice
  tail = search_terms[n/2 + 1:]

  # Pick another n/2 search terms randomly from common.txt
  # using random_search_term()
  for i in range(n/2):
    term = random_search_term(2)
    working_set.append(term)

  # Format a dict of {q, before, after} for search parameters.
  search_params = format_search_params("", random_window)

  # Call youtube_query to get the page containing
  # the least viewed search results.
  for search_term in working_set:
    search_term = search_term.encode("utf8") # encode to utf8 for executing the search request in youtube_query()
    search_params["q"] = search_term
    try:
     response = youtube_query(search_params)
    except UnicodeEncodeError as e:
      print e
      print "See response_error.log for details" 
      timestamp = time.strftime("%d.%m.%Y %H:%M:%S")
      with open("search_response.log", "a+") as f:
        f.write(timestamp + "\n")
        json.dump(response, f, indent=4, separators=(',', ': '), sort_keys=True)


    # If no results, skip to next search_term.
    if response is None:
      continue

    # Loop through items in the last page.
    print search_term

    items = response["items"]
    if last_only:
      items = items[-1:]  # last item as a list
    for item in reversed(items):
      vid_id = item["id"]["videoId"]
      stats = get_stats(vid_id)
      views = int(stats["views"])
      live = item["snippet"]["liveBroadcastContent"]
      link = "https://www.youtube.com/watch?v=" + vid_id

      # Check for no view items not having live content (past events with live content are not viewvable anymore).
      # items is reversed: if the current item has views, the rest can be skipped
      if views:
        break

      elif live == "none":
        title = item["snippet"]["title"]
        view_count = stats["views"]
        upload_date = stats["upload_date"]
        print title.encode("utf8")
        print link

        # Add info as a tuple to valid.
        data = {"title": title, "link": link, "views": view_count, "date": upload_date}
        valid.append(data)

      # No views, but has live content: print for logging purposes.
      else:
        print "liveBroadcastContent: ", live
        print link


  # Add valid to file, don't overwrite previous.
  with open(rpi_path + "links.json") as f:
    old = json.load(f)

  # Reopen in w mode to overwite previous data.
  # Note: non-ASCII characters in titles will be escaped with \uxxxx,
  # see documentation at https://docs.python.org/2/library/json.html
  with open(rpi_path + "links.json", "w") as f:
    valid.extend(old)
    json.dump(valid, f)

  # Store the rest of the index back to file or re-initialize it
  # if there nothing left to store.
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
  # Combine two or more common words for long search term.
  if nword > 1:
    with open(rpi_path + "common.txt") as f:
      lines = [line.rstrip("\n") for line in f]
      rand = random.sample(lines, nword)
      rand = " ".join(rand)

  # Use dict.txt for single word search terms.
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


def format_search_params(q, random_window = False):
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
    window = randomize_window()
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
def main(args):
  """Define procedures for each command line argument."""

  # --init
  # Initialize search_terms.json.
  if args.init:
    if isinstance(args.init, str):
      print "Initializing index starting from " + args.init + "..."
      init_bot(args.init)
    else:
      print "Initializing..."
      init_bot()


  # --tweet
  # Attempt to tweet the top item in links.json.
  elif args.tweet:
    tweet()
    print "\n"


  # --parse
  # Call zero_search() to store new links to links.json and measure execution time.
  # Only parse new links if < 10 items currently stored.
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
  # Perform a sample search to console, does not guarentee a zero view item.
  elif args.q:
    search_params = format_search_params(args.q, args.random_window)  # format a dict of parameters as required by youtube_query()
    response = youtube_query(search_params)
    if not response:
      print "No results"
    
    else:
      # Get all items from the last page of results.
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


  # No argument provided, show usage.
  else:
    parser.print_help()



#==============================================================================
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("-q", help = "Perform a sample search on given search term. Prints the items with least views to stdout.", metavar = "search_term")
  parser.add_argument("--tweet", help = "Tweet the next result stored in links.json.", action = "store_true")
  parser.add_argument("--init", help = "Create a search terms index at search_terms.json by reading dict.txt. \
    The optional argument determines the word to start building the index from.",
    nargs = "?", const = True, metavar = "search_term")
  parser.add_argument("--parse", help = "Parse n next search terms from search_terms.json for zero view items and store to links.json.", metavar = "n", type = int)
  parser.add_argument("--random-window", help = "Whether a randomized year long time window should be used when querying Youtube.\
    Affects the -q and --parse switches.", action="store_true")
  args = parser.parse_args()
  #print args

  
  try:
    main(args)
  except HttpError as e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
  except IOError as e:
    print e
    print "Try initialiazing this script with the --init switch"
  


  





