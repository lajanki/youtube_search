# youtube_search
A bot that tweets YouTube videos with no views.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and
  2. any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
bunch of search terms and saves the results with zero views to a buffer file.

The search terms are read from two source files:
  * dict.txt, containing > 71 000 individual words. Words read here are processed in groups of n files at a time.
  * common.txt, containing > 20 000 common English words. This file is used to generate random two word search terms to help narrow down the search.



## Requirements
##### Modules
* Google APIs Client Library:
  https://developers.google.com/api-client-library/python/start/installation
* Twython:
https://twython.readthedocs.org/en/latest/

##### Keys:
 * Google API Key:
https://developers.google.com/api-client-library/python/guide/aaa_apikeys
   * Store this key in the keys.json file.
   * **This key is required!** Running this script without it will result in an HTTP error with a message of "Daily Limit for Unauthenticated Use Exceeded".
 * Additionally the tweeting feature requires access tokens and keys from Twitter
 https://dev.twitter.com/oauth/overview/application-owner-access-tokens



## Usage
```
  --init           Create a search term index at search_terms.json by
                   processing dict.txt.
  --tweet          Tweet the next result stored in links.json.
  --parse n        Parse n next search terms from search_terms.json for zero
                   view items and store them to links.json.
  --random-window  Whether a randomized year long time window should be used
                   when querying Youtube.

```
First, initialize the bot by
```
python twitterbot.py --init
```
This creates a dynamic index file search_terms.json for search terms to bo read frm. Next, perform a search by running
```
python twitterbot.py --parse n
```
This takes the first n/2 words from the index, performs a search and stores results with no views to links.json. Another n/2 search terms are randomly generated from combining two common words in common.txt. To tweet the topmost result in links.json, run
```
python twitterbot.py --tweet
```
youtube_search.py is mainly a library module that performs the actual seraching, but it can also be run with
```
python youtube_search -q search_term
```
to perform a sample search using search_term as a search term. Output will be printed to stdout and consists of the last items returned by YouTube ordered by viewcount. They are not guaranteed to be zero view items.



Written on Python 2.7.8
