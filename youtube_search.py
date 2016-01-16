#!/usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# youtube_search.py
#
# Searches for YouTube videos with no or little (<10) views.
#
# The Google YouTube Data API comes with certain restrictions that prevents
# from directly searching for content with no views. Namely:
# 1)  one cannot use view count as a search parameter, and
# 2)  any search query will return at most 500 results.
#
# This script uses a brute force type approach by performing the search to a
# bunch of search terms and saves the results with <10 views to a file.
#
# The search terms are read from a dictionary file consisting of > 71 000 words.
# These words are read in groups of 50. Each time this script is executed
# either the top most result from the buffer file is chosen for output,
# or the next 50 words are processed.
#
# Changelog:
# 16.1.2016 - Code cleanup, added publishedBefore argument to youtube.search().list()
# 12.9.2015 - Initial release
#
# Lauri Ajanki 11.9.2015
#############################################################################
 

import time
import sys
import json
import random
import twython
import os
import argparse
import datetime
from oauth2client import tools
from apiclient.discovery import build
from apiclient.errors import HttpError
#from oauth2client.tools import argparser


# Change the default encoding in case the video title contains non-ASCII characters.
reload(sys)  
sys.setdefaultencoding("utf-8")

# Get required Twitter and Google keys from file.
with open("./keys.json") as f:
  KEYS = json.load(f)

# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = KEYS["GOOGLE_DEVELOPER_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


#========================================================================================
# Youtube query functions =
#==========================
def youtube_query(search_term, page_token = None):
  # Perform a YouTube query.
  # Args:
  #   search_term (string): the search term,
  #   page_token (string): a token used to access the next page of the result set.
  # Return:
  #   a dictionary object representing the next page token of the result set and a video title and id of
  #   the least viewed item of current page.
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

  # create a timestamp to be used as a publishedBefore argument
  d = datetime.datetime.utcnow()
  #d = d.isoformat("T") + "Z"
  d_year_ago = d - datetime.timedelta(days=365)
  d_year_ago = d_year_ago.isoformat("T") + "Z"
  # Call the search.list method to retrieve results matching the specified
  # query term. See the API at
  # https://developers.google.com/resources/api-libraries/documentation/youtube/v3/python/latest/youtube_v3.search.html
  search_response = youtube.search().list(
    q=search_term,
    part="id,snippet",
	publishedBefore=d_year_ago,
    relevanceLanguage="en",
    maxResults=50,
    order="viewCount",
    pageToken = page_token,
    type = "video" 
  ).execute()

  # See if the response contains more pages.
  if "nextPageToken" in search_response.keys():
    page_token = search_response["nextPageToken"]
  else:
    page_token = None

  # Get the last item (least views) from the current page of result set.
  try:
    title = search_response.get("items")[-1]["snippet"]["title"]
    vid_id = search_response.get("items")[-1]["id"]["videoId"]
  except IndexError:
    print "No search results", search_term
    return None

  return { "page_token":page_token, "title":title, "vid_id":vid_id }


def zero_search(search_term):
  # Perform the actual search: call youtube_query until no more pages left
  # and get the last result.
  # Args:
  #   search_term: string, the search term.
  # Return:
  #   a dictionary object representing the title, url, view count and upload date
  #   of the least viewed item.
  print "Search term:", search_term

  res = youtube_query(search_term)
  token = res["page_token"]
  title = res["title"]
  vid_id = res["vid_id"]

  while token != None:
    res = youtube_query(search_term, token)
    token = res["page_token"]
    title = res["title"]
    vid_id = res["vid_id"]

  viewcount, date = get_stats(vid_id)
  url = "https://www.youtube.com/watch?v="+vid_id

  return { "title":title, "url":url, "viewcount":viewcount, "date":date }


def get_stats(vid_id):
  # Get view count and upload date for the given video.
  # Arg:
  #  vid_id (string): a Youtube video id
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
  
  stats = youtube.videos().list(
    part="statistics,snippet",
    id=vid_id
  ).execute()

  viewcount = stats.get("items")[0]["statistics"]["viewCount"]
  date = stats.get("items")[0]["snippet"]["publishedAt"]

  # date is in ISO format (YYYY-MM-DD), reformat to DD.MM.YYYY 
  d = date[8:10]
  m = date[5:7]
  y = date[0:4]
  date = d+"."+m+"."+y

  return viewcount, date


#========================================================================================
# I/O functions =
#================
def random_search_term():
  # Get a random search term from file.
  # Return:
  #  the search term
  with open("./dict.txt") as f:
    lines = [line.rstrip("\n") for line in f]
    rand = random.choice(lines)
  return rand


def store_links():
  # Parse the search terms returned by next_slice for videos with
  # less than 10 views. Store the links to links.dat file.
  slice, pos = next_slice()

  with open("./links.dat", "w+") as f:  # overwrites previous links
    for search_term in slice:
      try:  # res != None
        res = zero_search(search_term)
        title = res["title"]
        url = res["url"]
        viewcount = res["viewcount"]
        date = res["date"]

        if int(viewcount) < 10:
          print title
          print url
          print viewcount
          print date
          data = title+","+url+","+viewcount+","+date+"\n"
          f.write(data)

      except TypeError as e:
        print e
        print "No search result:", search_term


    # Write the byteindex to mark the beginning of the next 50 words
    # to the end of the file.
    f.write(str(pos))

  print "Done"


def next_slice():
  # Get the next 50 search terms from file.
  # Return:
  #   a list of the search terms and a byte index used to
  #   tell where the next slice should be read from.
  slice = []

  try:
    # Read the byte index from the end of the file.
    with open("./links.dat") as links:
      lines = [line.rstrip("\n") for line in links]
      start = int(lines.pop())
  except IOError:
    start = 0

  # Seek to the position marked by start and read 50 lines.
  with open("./dict.txt") as f:
    f.seek(start)
    for i in range(50):
      slice.append(f.readline().rstrip("\n"))
    pos = f.tell()

  return slice, pos


#========================================================================================
def bot():
  # Read the topmost link from links.dat and post it to Twitter.

  # First time calling this script and links.dat does not exist => create it.
  if not os.path.isfile("./links.dat"):
    print "The file links.dat does not exist. Generating...\n\
Please wait, this may take a while."
    store_links()

  with open("./links.dat") as f:
    lines = [line.rstrip("\n") for line in f]

    # Previous call to store_links did not result in valid links (links.dat contains only
    # the byte index), call it again and exit.
    if len(lines) <= 1:
      print "Error: no links in links.dat, generating new ones..."
      store_links()
      print "Try running this script again."
      sys.exit()

  # Pick the topmost link, parse it to a list of [title, url, viewcount, date].
  link = lines[0].split(",")
  rest = lines[1:]

  # Tweet
  msg = link[0] + "\n" + link[1] + "\n" + "uploaded: " + link[3] + "\n" + "views: " + link[2]
  API_KEY = KEYS["API_KEY"]
  API_SECRET = KEYS["API_SECRET"]
  OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
  OAUTH_SECRET = KEYS["OAUTH_SECRET"]

  t = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)
  t.update_status(status=msg)
  
  print msg
  print time.strftime("%d.%m.%Y-%H:%M:%S")

  # Write the rest back to file or generate new links if the one picked was the last one.
  if len(rest) > 1:
    with open("./links.dat", "w+") as f:  # overwrites previous data
      for item in rest:
        f.write(item+"\n")

  else:
    print "No links left, generating new ones..."
    store_links()


#========================================================================================
# Main =
#=======
def main():
  parser = argparse.ArgumentParser(parents=[tools.argparser], description="Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("-q", help="Perform a sample search. Uses a random search term from dict.txt if not specified. Unlike the bot feature, this is for testing purposes and doesn't guarentee a seldom seen result.", nargs="?", const=random_search_term(), metavar="search term")
  parser.add_argument("--bot", help="Tweet the next result from links.dat", action="store_true")
  parser.add_argument("--init", help="Remove links.dat", action="store_true")
  args = parser.parse_args()

  if args.bot:
    bot()
  elif args.q:
    res = zero_search(args.q)
    print "Title:", res["title"]
    print "URL:", res["url"]
    print "View count", res["viewcount"]
    print "Uploaded:", res["date"]
  elif args.init:
    os.remove("./links.dat")
    print "links.dat removed, use the bot feature to generate a new one."
  else:
    parser.print_help()


if __name__ == "__main__":
  try:
    main()
  except HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)







