#!/usr/bin/python
# -*- coding: utf-8 -*-

###############################################################################
# youtube_search.py                                                           #
#                                                                             #
# Searches for YouTube videos with no views (by default)                      #
#                                                                             #
# The Google YouTube Data API comes with certain restrictions that prevents   #
# from directly searching for content with no views. Namely:                  #
# 1)  one cannot use view count as a search parameter, and                    #
# 2)  any search query will return at most 500 results.                       #
#                                                                             #
# This script uses a brute force type approach by performing the search to a  #
# bunch of search terms and saves the results with zero views to a file.      #
#                                                                             #
# The search terms are read from a dictionary file consisting of ~ 71 000     #
# words. The script runs around a buffer based system: the words are read     #
# in groups of 50, these are then queried against the YouTube API and valid   #
# results are stored to file (links.pkl). The next runs of the script then    #
# tweets the topmost result until the file is exhausted and the next 50       #
# search terms are processed for new results.                                 #
#                                                                             #
# Changelog:                                                                  #
# 3.4.2016                                                                    #
#   * Querying: changed paginitaion in youtube_query() to use the API's       #
#     list_next() method                                                      #
#   * Parsing: zero_search() now parses more than one results per search term #
#     (by default, all items in the last page of the results)                 #
#   * Parsing: search results with liveContent == "upcoming" are now          #
#     considered invalid (results to "upcoming" videos that have already      #
#     occured and can no longer be viewed, maybe find out why this            #
#     is happening?)                                                          #
#   * Maintenance: added an --empty switch for emptying links.pkl             #
#                                                                             #
# 25.2.2016                                                                   #
#   * I/O: output is now stored as pickle encoded dicts (links.pkl)           #
#     instead of a raw csv text file.                                         #
#   * I/O: added a dynamic index file (search_terms.pkl) to keep track of     #
#     which words to read next, no more cumbersome byte index method.         #
#   * Code cleanup: the zero search part is now down to 1 function,           #
#     (zero_search()) and the bot feature is moved directly under main()      #
#                                                                             #
# 16.1.2016                                                                   #
#   * Code cleanup: added publishedBefore argument to                         #
#     youtube.search().list()                                                 #
#                                                                             #
# 12.9.2015                                                                   #
#   * Initial release                                                         #
###############################################################################
 

import time
import json
import random
import twython
import argparse
import datetime
import pickle
import pprint
from apiclient.discovery import build
from apiclient.errors import HttpError


# Read the required Twitter and Google keys from file.
with open("keys.json") as f:
  keys = json.load(f)

# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = keys["GOOGLE_DEVELOPER_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


#==============================================================================
# Initialization =
#=================
def init(start=None):
  """Read contents of dict.txt and store it as a list in search_terms.pkl,
  which will be modified later.
  Arg:
    start (string): the search term to start building the index, one of the
    search terms in dict.txt.
  Return:
    None
  """
  with open("dict.txt", "r") as f:
    search_terms = f.read().splitlines()  # read to a list split by newlines

  if start:
    try:
      idx = search_terms.index(start)
      search_terms = search_terms[idx:]
    except ValueError as e:
      print e
      print "Using the full index."

  with open("search_terms.pkl", "wb") as index:
    pickle.dump(search_terms, index, 2)

  # init an empty links.pkl
  with open("links.pkl", "wb") as links:
    pickle.dump([], links, 2)


#========================================================================================
# Youtube query functions =
#==========================
def youtube_query(search_term):
  """Query YouTube on the given search term ordered by viewcount
  and return the final page of results.
  Arg:
    search_term (string): the search term
  Return:
    the final page of the results as a JSON encoded response object
  """
  # create a search request
  d = datetime.datetime.utcnow()
  year_ago = d - datetime.timedelta(days=365)
  year_ago = year_ago.isoformat("T") + "Z"

  request = youtube.search().list(
    q=search_term,
    part="id,snippet",
    publishedBefore=year_ago,
    relevanceLanguage="en",
    maxResults=50,
    order="viewCount",
    type = "video"
  )

  # call list_next() until no more pages to fetch
  while request is not None:
    response = request.execute()
    request = youtube.search().list_next(request, response)

  return response


def zero_search(n=35, last_only=False):
  """Read the n topmost search terms from search_terms.pkl
  and parse them for zero view videos. Store results to
  links.pkl.
  Args:
    n (int): the number of search terms to read
    last_only (boolean): whether only the last item (= least views) of the YouTube query
      results should be processed
  Return:
    None
  """
  with open("search_terms.pkl", "rb") as index:
    search_terms = pickle.load(index)

  valid = []  # a list for zero view items

  # get the first n search terms from file
  next_slice = search_terms[:n]
  tail = search_terms[n+1:]

  # call youtube_query2 to get the page containing
  # the least viewed search results
  for search_term in next_slice:
    response = youtube_query(search_term)

    # loop through items in the last page
    #pprint.pprint(response["items"])
    #print search_term

    items = response["items"]
    if last_only:
      items = items[-1:]  # list containing only the last item
    print "no. items: ", len(items)
    for item in reversed(items):
      vid_id = item["id"]["videoId"]
      stats = get_stats(vid_id)
      views = int(stats["views"])
      live = item["snippet"]["liveBroadcastContent"]
      print views, "live content: ", live

      # check for no view items not having live content.
      # items is reversed: if the current item has views, the rest can be skipped
      if views:
        break

      elif live == "none":
        title = item["snippet"]["title"]
        link = "https://www.youtube.com/watch?v="+vid_id
        view_count = stats["views"]
        upload_date = stats["upload_date"]
        print title
        print link

        # add info as a tuple to valid
        valid.append((title, link, view_count, upload_date))


    # store valid to file
    with open("links.pkl", "wb") as links:
      pickle.dump(valid, links, 2)

    # store the rest of the index back to file or re-initialize it
    # if nothing to store
    if tail:
      with open("search_terms.pkl", "wb") as index:
        pickle.dump(tail, index, 2)
    else:
      init()


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
    part="statistics,snippet",
    id=vid_id
  ).execute()

  viewcount = stats["items"][0]["statistics"]["viewCount"]
  date = stats["items"][0]["snippet"]["publishedAt"]

  # date is in ISO format (YYYY-MM-DD), reformat to DD.MM.YYYY 
  d = date[8:10]
  m = date[5:7]
  y = date[0:4]
  date = d+"."+m+"."+y

  return { "views": viewcount, "upload_date": date }


def random_search_term():
  """
  Get a random search term from dict.txt.
  Return:
    the search term
  """
  with open("/dict.txt") as f:
    lines = [line.rstrip("\n") for line in f]
    rand = random.choice(lines)
  return rand


#==============================================================================
# Main =
#=======
def main():
  parser = argparse.ArgumentParser(description="Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("-q", help="Perform a sample search. Uses a random search term from dict.txt if not specified.", nargs="?", const=random_search_term(), metavar="search term")
  parser.add_argument("--bot", help="Tweet the next result from links.dat", action="store_true")
  parser.add_argument("--init", help="Initialize an empty set of links and create a search index by reading dict.txt. An optional argument matching a search term in dict.txt can be provided to mark the starting point of the index.", nargs="?", const=True, metavar="search term")
  parser.add_argument("--show", help="Show contents of links.pkl.", action="store_true")
  parser.add_argument("--empty", help="Soft initialization: empty links.pkl but keep the index intact.", action="store_true")
  args = parser.parse_args()

  #========#
  # --init #
  #========#
  if args.init:
    if isinstance(args.init, str):
      print "Initializing index starting from "+args.init+"..."
      init(args.init)
    else:
      print "Initializing..."
      init()

  #========#
  # --show #
  #========#
  elif args.show:
    with open("links.pkl", "rb") as links:
      link_data = pickle.load(links)
    pprint.pprint(link_data)

  #=========#
  # --empty #
  #=========#
  elif args.empty:
    with open("links.pkl", "wb") as links:
      pickle.dump([], links, 2)

  #==================================================#
  # --bot, either:                                   #
  #   1 tweet the next link from links.pkl, or       #
  #   2 call zero_search to generate the next links  #
  #==================================================#
  elif args.bot:
    with open("links.pkl", "rb") as links:
     link_data = pickle.load(links)

    # 1 check if there is something to tweet
    if link_data:
      new = link_data.pop(0)  # (title, link, view_count, upload_date)

      # tweet
      msg = new[0] + "\n" + new[1] + "\n" + "uploaded: " + new[3] + "\n" + "views: " + new[2]
      surplus = len(msg) - 140
      if surplus > 0:
        msg = new[0][:-surplus] + "\n" + new[1] + "\n" + "uploaded: " + new[3] + "\n" + "views: " + new[2]
        print "Title cut to keep tweet within 140 characters."

      API_KEY = keys["API_KEY"]
      API_SECRET = keys["API_SECRET"]
      OAUTH_TOKEN = keys["OAUTH_TOKEN"]
      OAUTH_SECRET = keys["OAUTH_SECRET"]
      twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
      twitter.update_status(status=msg)
  
      print msg
      print time.strftime("%d.%m.%Y %H:%M:%S")

      # write the rest of link_data back to file
      with open("links.pkl", "wb") as links:
        pickle.dump(link_data, links, 2)

    # 2 call zero_search
    else:
      print "links.pkl is empty, fetching new links..."
      zero_search()
      print "Done. Run again to tweet the next result."


  #===================#
  # -q, sample search #
  #===================#
   elif args.q:
    response = youtube_query(args.q)

    # get the last item from the response
    res = response["items"][-1]

    vid_id = res["id"]["videoId"]
    stats = get_stats(vid_id)
    views = int(stats["views"])

    title = res["snippet"]["title"]
    link = "https://www.youtube.com/watch?v="+vid_id
    view_count = stats["views"]
    upload_date = stats["upload_date"]
    print title
    print link
    print "views:", views
    print "uploaded:", upload_date

  #==================================#
  # no argument provided, show usage #
  #==================================#
  else:
    parser.print_help()


#==============================================================================
if __name__ == "__main__":
  try:
    main()
  except HttpError as e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
  except IOError as e:
    print e
    print "Try initialiazing this script with the --init switch"
  





