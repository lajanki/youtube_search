#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A runnable front to youtube_search.py. This is mainly for demonstartion purposes. Picks a number of
search terms from dict.txt and prints a list of items with no views.
"""

import argparse

import youtube_search


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Performs sample YouTube searches.")
    parser.add_argument("n", help="Number of search terms to use", type=int)
    args = parser.parse_args()

    app = youtube_search.VideoCrawler()
    app.run(args.n)
