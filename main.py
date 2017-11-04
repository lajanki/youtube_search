#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
A runnable front to youtube_search.py. This is mainly for demonstartion purposes. Picks a number of
search terms from dict.txt and prints a list of items with no views.
"""

import argparse
import random
import codecs

import youtube_search


def main(args):
    """Parse for new videos or initialize the index."""
    app = youtube_search.VideoCrawler()

    if args.search:

        # choose a random sample of search terms
        with codecs.open("./dict.txt", encoding="utf-8") as f:
            search_terms = f.read().splitlines()
            sample = random.sample(search_terms, args.search/2)

        crawler = youtube_search.VideoCrawler()
        combined = crawler.generate_random_search_terms(args.search/2, 2)

        search_terms = sample + combined
        zeros = crawler.zero_search(search_terms)

        if not zeros:
            print "No results found"

        else:
            print "Found the following results:"
            for result in zeros:
                print "title:", result["title"]
                print "url:", result["url"]
                print "views:", result["views"]
                print "uploaded:", result["date"]
                print




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Search for YouTube videos with no views.")
    parser.add_argument("--search", help = "Search using n random search terms from dict.txt and common.txt", metavar = "n", type = int)
    args = parser.parse_args()

    main(args)
