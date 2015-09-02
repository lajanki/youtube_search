#!/usr/bin/python
# -*- coding: utf-8 -*-

##########################################################################################
# youtube_search.py                                                                      #
# Attempts to find YouTube videos with little or no views using random or                #
# specified search terms.                                                                #
#																						 #
# The Google YouTube Data API comes with certain restrictions that prevents from         #
# directly searching for content with no views. Namely:                                  #
#  1) one cannot use view count as a search parameter, and                               #
#  2) any search query will return at most 500 results.                                  #
# Instead this script uses a random search term, orders the results by view count and    #
# chooses the last result.                                                               #
#                                                                                        #
# Additioanlly a radom week long timeframe from one year ago to three years ago is       #
# specified as search parameter to narrow the results.                                   #
#                                                                                        #
# This script does not make any guarantees about the outcome: the results may have       #
# zero or several views or, with a bad search term, no results at all.                   #
#                                                                                        #
# Requires:                                                                              #
#  Modules                                                                               #
#  * Google APIs Client Library:                                                         #
#      https://developers.google.com/api-client-library/python/start/installation        #
#  * Twython:                                                                            #
#      https://twython.readthedocs.org/en/latest/                                        #
#  Keys:                                                                                 #
#  * Google API Key:                                                                     #
#      https://developers.google.com/api-client-library/python/guide/aaa_apikeys         #
#  * Additionally the Twitter bot-feature requires access tokens and keys from Twitter   #
#      https://dev.twitter.com/oauth/overview/application-owner-access-tokens            #
#                                                                                        #
# Lauri Ajanki 31.8.2015                                                                 #
##########################################################################################
 
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import datetime, time, sys, json, random, twython


# Get YouTube and Twitter authentication keys from external JSON file.
# NOTE: THIS FILE IS EMPTY, you need to fill it with your own keys!
with open("./keys.json") as f:
  KEYS = json.load(f)

# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = KEYS["GOOGLE_DEVELOPER_KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Create a global service object to interact with the YouTube API.
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)


# Get a random search term from the specified text file.
def get_search_term():
  with open("./dict.txt") as f:
    lines = [line.rstrip("\n") for line in f]
    rand = random.choice(lines)
    return rand


# Perform the YouTube search using a randomized search term and a week long timeframe.
# Return:
#   page_token: a pagination token used to continue the same search for more results,
#   title: the title to the last video of the result set,
#   vid_id: an id to the last video of the result set. The URL to a YouTube videos are
#           of the form https://www.youtube.com/watch?v=<vid_id> 
def get_pages(search_term, weeks, page_token = None):
  # Get todays date and subtract (1 year + random amount of weeks) to get publishedBefore
  # publishedAfter parameters.
  year = int(time.strftime("%Y"))
  month = int(time.strftime("%m"))
  day = int(time.strftime("%d"))

  # Convert to RFC 3339 format.
  d = datetime.datetime(year, month, day)
  d_i = d + datetime.timedelta(days=-1*365 - 7*weeks)
  d_f = d + datetime.timedelta(days=-1*365 - 7*(weeks-1))

  d_i = d_i.isoformat() + "Z"
  d_f = d_f.isoformat() + "Z"

  # Call the search.list method to retrieve results matching the specified
  # query term.
  # See the API for help:
  # https://developers.google.com/resources/api-libraries/documentation/youtube/v3/python/latest/youtube_v3.search.html
  search_response = youtube.search().list(
    q=search_term,
    part="id,snippet",
    relevanceLanguage="en",
    maxResults=50,
    order="viewCount",
    publishedBefore=d_f,
    publishedAfter=d_i,
    pageToken = page_token,
    type = "video" 
  ).execute()

  # Check if there are more results to fetch later.
  if "nextPageToken" in search_response.keys():
    page_token = search_response["nextPageToken"]
  else:
    page_token = None

  # Get the last result of the result set.
  # Exit if no results.
  try:
    title = search_response.get("items")[-1]["snippet"]["title"]
    vid_id = search_response.get("items")[-1]["id"]["videoId"]
  except IndexError:
	print "No search results:", search_term
	sys.exit(1)

  return page_token, title, vid_id


# Get view count and upload date of the video given by id.
def get_stats(vid_id):
  stats = youtube.videos().list(
    part="statistics,snippet",
    id=vid_id
  ).execute()

  viewcount = stats.get("items")[0]["statistics"]["viewCount"]
  date = stats.get("items")[0]["snippet"]["publishedAt"]
  date = date[:10]  # date is in RFC 3339 format; only get the first 10 characters eg. 2013-06-11 
  return viewcount, date


# Same as main() excepts potst the output to Twitter using twython module. See
# https://twython.readthedocs.org/en/latest/usage/basic_usage.html
# Always uses a random search term.
def yt_search_bot():
  # get keys from keys.json. Note that KEYS is a global dictionary object.
  API_KEY = KEYS["API_KEY"]
  API_SECRET = KEYS["API_SECRET"]
  OAUTH_TOKEN = KEYS["OAUTH_TOKEN"]
  OAUTH_SECRET = KEYS["OAUTH_SECRET"]
  
  t = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

 
  search_term = get_search_term()
  print "Search term:", search_term

  week = random.randint(0, 2*52)
  token, title, vid_id = get_pages(search_term, week)
  
  while token != None:
    token, title, vid_id = get_pages(search_term, week, token)

  viewcount, date = get_stats(vid_id)

  url = "https://www.youtube.com/watch?v="+vid_id  
  print title
  print url
  print "uploaded: "+date+", "+"views:"+viewcount

  msg = title + "\n" + url + "\n" + "uploaded: " + date + "\n" + "views: " + viewcount
  t.update_status(status=msg)  


#*******
# Main *
#*******

# Performs the search and prints the result to console window.
def main(args):
  # if no search term was specified, use one at random
  search_term = args.q
  if search_term == None:
    search_term = get_search_term()
    print "Search term:", search_term

  # randomize a week to determine the timeframe for the search
  week = random.randint(0, 2*52)
  token, title, vid_id = get_pages(search_term, week)
  
  # continue the search if there are more than one page
  while token != None:
    token, title, vid_id = get_pages(search_term, week, token)

  viewcount, date = get_stats(vid_id)

  print title
  print "https://www.youtube.com/watch?v="+vid_id
  print "uploaded:", date
  print "view count:", viewcount




if __name__ == "__main__":
  argparser.add_argument("--q", help="Search term", default=None)
  argparser.add_argument("--bot", help="Use bot", action="store_true")
  args = argparser.parse_args()

  try:
    if args.bot:
      yt_search_bot()
    else:
      main(args)
  except HttpError, e:
    print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
