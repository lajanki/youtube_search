#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Uses youtube_search.py to parse for links to zer oview items and tweets them one at a time.
"""

import os
import json
import twython
import argparse
import logging
import youtube_search

base = "bot-data/"
links_storage = base + "links.json"

logging.basicConfig(
	filename = "bot.log",
	format = "%(asctime)s %(message)s",
	datefmt = "%d.%m.%Y %H:%M:%S",
	level = logging.INFO
)
logger = logging.getLogger(__name__)

def init_bot():
	"""Initialize the bot by creating the base folder (if not already present) with an initilized
	index.json and an empty links.json
	"""
	if not os.path.isdir(base):
		os.mkdir(base)

	app = youtube_search.VideoCrawler(base)
	app.search_term_index.refresh()
	with open(links_storage, "w") as f:
		json.dump([], f)

def parse_new_links(n):
  """Use the crawler to search for zero view videos and store them in links.json.
  Args:
    n (int): number of items to parse: n/2 search terms are picked from the index and n/2 are randomly generated
  """
  # get current contents of links.json
  with open(links_storage) as f:
    link_data = json.load(f)

  app = youtube_search.VideoCrawler(base)
  try:
    search_term_slice = app.search_term_index.get_slice(n/2)
    randomized = app.generate_random_search_terms(n/2, 2)
    search_terms = search_term_slice + randomized
    new_links = app.zero_search(search_terms)

    if new_links:
      # Add new links to old and store back to file.
      link_data.extend(new_links)
      with open(links_storage, "w") as f:
        json.dump(link_data, f)

      logger.info("Added {} new links to links.json".format(len(new_links)))

    else:
      logger.info("No new links detected")

  # refresh (but don't do any parsing), on empty index
  except youtube_search.IndexEmptyException as err:
    logger.info("index.json is empty, refreshing")
    app.search_term_index.refresh()

def parse_if_low(threshold, n):
  """Wrapper to parse_new_links: parses for new links only if there are < threshold
  links currently stored.
  Args:
    threshold (int): minimum number of links required to parse for new links
    n (int): number of search terms to parse
  """
  with open(links_storage) as f:
    link_data = json.load(f)

  if len(link_data) < threshold:
    parse_new_links(n)
  else:
    logger.info("{} links left in links.json, no action taken".format(len(link_data)))

def tweet():
  """Attempts to tweet the topmost item from links.json. Prints an error message if
  there are nothing to tweet.
  """
  with open("./keys.json") as f:
    keys = json.load(f)

  API_KEY = keys["TWITTER_API_KEY"]
  API_SECRET = keys["TWITTER_API_SECRET"]
  OAUTH_TOKEN = keys["TWITTER_OAUTH_TOKEN"]
  OAUTH_SECRET = keys["TWITTER_OAUTH_SECRET"]
  twitter = twython.Twython(API_KEY, API_SECRET, OAUTH_TOKEN, OAUTH_SECRET)

  with open(links_storage) as f:
    link_data = json.load(f)

  try:
    link = link_data.pop(0)
    url = link["url"]

    # Format a message to tweet:
    # for long tweets, cut the title to 75 characters
    # url = 23 characters (after Twitter's own link shortening, see https://support.twitter.com/articles/78124)
    # date = 20
    # views ~ 8
    # linebreaks = 3
    # => title: first 70 characters + "..."
    title = link["title"]
    if len(title) > 75:
      title = title[:72] + "..."

    msg = "{}\n{}\nuploaded: {}\nviews: {}".format(title, url, link["date"], link["views"])

    # Encode the message for network I/O
    msg = msg.encode("utf8")
    twitter.update_status(status = msg)

    # Write the rest of link_data back to file.
    with open(links_storage, "w") as f:
      json.dump(link_data, f)

  # something went wrong with tweeting
  except twython.exceptions.TwythonError as err:
    logger.info(err)
    print err

  # couldn't pop from links.json
  except IndexError as err:
    msg = "links.json is empty"
    logger.info(msg)
    print msg

def get_bot_status():
    """Get the number of links currently stored in links.json and index.json."""
    with open(links_storage) as f:
      link_data = json.load(f)

    with open(base + "index.json") as f:
      index = json.load(f)

    return {"links": len(link_data), "index": len(index)}

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description = "Search for and tweet Youtube videos with no or little views.")
  parser.add_argument("--tweet", help = "Tweet the next result stored in links.json.", action = "store_true")
  parser.add_argument("--parse", help = "Parse n next search terms from search_terms.json for zero view items and store them to links.json.", metavar = "n", type = int)
  parser.add_argument("--stats", help = "Prints number of items left in links.json and index.json", action = "store_true")
  parser.add_argument("--init", help = "Initialize the bot by creating a file structure in bot-data/", action = "store_true")
  args = parser.parse_args()

  if args.init:
	init_bot()

  elif args.tweet:
    tweet()

  elif args.parse:
    parse_if_low(10, args.parse)

  elif args.stats:
    stats = get_bot_status()
    print "{} links in links.json and {} search terms in index.json".format(stats["links"], stats["index"])
