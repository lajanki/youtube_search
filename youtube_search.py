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
#==================
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
def youtube_query(search_term, page_token = None):
  """Perform a YouTube query.
  Args:
    search_term (string): the search term,
    page_token (string): a token used to access the next page of the result set.
  Return:
    a dictionary object representing the next page token of the result set and a video title and id of
    the least viewed item of the current page.
  """
  # create a timestamp to be used as a publishedBefore argument
  d = datetime.datetime.utcnow()
  year_ago = d - datetime.timedelta(days=365)
  year_ago = year_ago.isoformat("T") + "Z"
  # Call the search.list method to retrieve results matching the specified
  # query term. See the API at
  # https://developers.google.com/resources/api-libraries/documentation/youtube/v3/python/latest/youtube_v3.search.html
  search_response = youtube.search().list(
    q=search_term,
    part="id,snippet",
	  publishedBefore=year_ago,
    relevanceLanguage="en",
    maxResults=50,
    order="viewCount",
    pageToken = page_token,
    type = "video" 
  ).execute()

  # get the next token, title and the id of the last item of the current page
  page_token = search_response.get("nextPageToken")  # get() returns None if nextPageToken not in search_response
  last_page = search_response.get("items")[-1]

  title = last_page["snippet"].get("title")
  vid_id = last_page["id"].get("videoId")

  return { "page_token":page_token, "title":title, "vid_id":vid_id, "page":last_page }


def zero_search(n=20, view_treshold=0):
  """Read the n topmost search terms from search_terms.pkl
  and parse them for zero view videos. Store results to
  links.pkl.
  Arg:
    n (int): the number of search terms to read
    view_treshold (int): the maximum amount of views valid
    results should have
  Return:
    None
  """
  with open("search_terms.pkl", "rb") as index:
    search_terms = pickle.load(index)

  valid = []
  # get the first n search terms
  next_slice = search_terms[:n]
  tail = search_terms[n+1:]

  for search_term in next_slice:
    # parse for zero view result:
    # call youtube_query until last page of results
    res = youtube_query(search_term)
    token = res["page_token"]
    while token != None:
      res = youtube_query(search_term, page_token=token)
      token = res["page_token"]

    # check viewcount of the item returned and, if applicable,
    # add to valid
    vid_id = res["vid_id"]
    stats = get_stats(vid_id)
    if int(stats["views"]) <= view_treshold:
      title = res["title"]
      link = "https://www.youtube.com/watch?v="+vid_id
      view_count = stats["views"]
      upload_date = stats["upload_date"]

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
    res = youtube_query(args.q)
    token = res["page_token"]
    while token != None:
      res = youtube_query(args.q, page_token=token)
      token = res["page_token"]

    stats = get_stats(res["vid_id"])
    print "Title:", res["title"]
    print "URL:", "https://www.youtube.com/watch?v="+res["vid_id"]
    print "View count", stats["views"]
    print "Uploaded:", stats["upload_date"]

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
  





