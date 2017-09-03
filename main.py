#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse

import youtube_search

"""
A runnable front to youtube_search.py. This is mainly for demonstartion purposes. Picks a number of
search terms from the index and prints a list of items with no views.
"""


def main(args):
    """Parse for new videos or initialize the index."""
    app = youtube_search.VideoCrawler()

    if args.parse:
        try:
            print "Parsing for videos..."
            # get the next n/2 search terms from the index
            search_term_slice = app.search_term_index.get_slice(args.parse/2)
            # generate another n/2 from common.txt
            randomized = app.generate_random_search_terms(args.parse/2, 2)

            search_terms = search_term_slice + randomized
            results = app.zero_search(search_terms)

            if not results:
                print "No results found"

            else:
                print "Found the following results:"
                for result in results:
                    print "title:", result["title"]
                    print "url:", result["url"]
                    print "views:", result["views"]
                    print "uploaded:", result["date"]
                    print

        except youtube_search.IndexEmptyException as err:
            print "Search term index at {} is empty. Reinitialize it with --init and try again.".format(app.search_term_index.path)
        except:
            print "Something went wrong!"
            raise

    elif args.init:
        app.search_term_index.refresh()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Search for YouTube videos with no views.")
    parser.add_argument("--init", help = "Create a search term index file by processing dict.txt.", action = "store_true")
    parser.add_argument("--parse", help = "Parse n search terms from the index for zero views", metavar = "n", type = int)
    args = parser.parse_args()

    main(args)
