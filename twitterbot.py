#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
tweet_bot.py

Tweets youtube videos with no views detected by youtube_search.py.

Changelog:
11.1.2017
  * Initial version.

"""
 
import json
import twython
import argparse
import youtube_search



def tweet(video_parser):
  """Attempts to tweets the topmost item from links.json.
  Arg:
    file_path (string): path to the folder where links.json and keys.json are stored.
  """
  file_path = video_parser.path
  with open(file_path + "keys.json") as f:
    keys = json.load(f)

  API_KEY = keys["TWITTER_API_KEY"]
  API_SECRET = keys["TWITTER_API_SECRET"]
  OAUTH_TOKEN = keys["TWITTER_OAUTH_TOKEN"]
  OAUTH_SECRET = keys["TWITTER_OAUTH_SECRET"]
  twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

  with open(file_path + "links.json", "r") as f:
    link_data = json.load(f)

  # Check if there actually is something to tweet
  if link_data:
    link = link_data.pop(0)
    url = link["url"]

    # Format a message to tweet:
    # for long tweets, cut the title to 75 characters
    # url = 23 characters (after Twitter's own shortening, see https://support.twitter.com/articles/78124)
    # date = 20
    # views ~ 8
    # linebreaks = 3
    # => title: first 70 characters + "..."
    if len(link["title"]) > 75:
      title = link["title"][:72] + "..."
      video_parser.logger.info("Title cut to keep tweet within 140 characters.")
      #print "Title cut to keep tweet within 140 characters."
    else:
      title = link["title"]

    msg = title + "\n" + link["url"] + "\n" + "uploaded: " + link["date"] + "\n" + "views: " + link["views"]

    # Encode to uft8 for printing and sending to Twitter.
    msg = msg.encode("utf8")

    try:
      twitter.update_status(status = msg)
    except twython.exceptions.TwythonError as e:
      video_parser.logger.error(str(e))
      video_parser.logger.error("Attempted to tweet %s characters: %s", len(msg), msg)

    video_parser.logger.info("Tweeted %s", msg)
      
    # Write the rest of link_data back to file.
    with open(file_path + "links.json", "w") as f:
        json.dump(link_data, f)

  else:
    video_parser.logger.info("links.json is empty")


def parse_new_links(video_parser, n, random_window):
  """Search for new videos to tweet and append them to links.json.
  Only actually does anything if < 10 items currently in links.json.
  Args:
    video_parser (YoutubeParser): a reference to a YoutubeParser object performing the actual parsing.
    n (int): number of items to parse.
  """
  # Load current links to memory
  with open(video_parser.path + "links.json") as f:
    old = json.load(f)

  # Don't do anything if >= 10 items already in links.json
  if len(old) >= 10:
    video_parser.logger.info("%s items still in links.json, no action taken.", len(old))
    return

  links = video_parser.zero_search(n, random_window)

  # Add new links to old and store back to file.
  old.extend(links)
  with open(video_parser.path + "links.json", "w") as f:
    json.dump(old, f)


#==============================================================================

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("--init", help = "Create a search term index at search_terms.json by processing dict.txt.", action = "store_true")
  parser.add_argument("--tweet", help = "Tweet the next result stored in links.json.", action = "store_true")
  parser.add_argument("--parse", help = "Parse n next search terms from search_terms.json for zero view items and store them to links.json.", metavar = "n", type = int)
  parser.add_argument("--random-window", help = "Whether a randomized year long time window should be used when querying Youtube.", action="store_true")
  args = parser.parse_args()
  #print args


  video_parser = youtube_search.YoutubeParser()

  # Rebuild search_terms.json.
  if args.init:
    video_parser.create_index()

  # Tweet the topmost item in links.json.
  elif args.tweet:
    tweet(video_parser)

  # Parse for new links if < 10 items currently in links.json.
  elif args.parse:
    parse_new_links(video_parser, args.parse, args.random_window)
