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
  -q search_term        Perform a sample search on given search term. Prints
                        the items with least views to stdout.
  --tweet               Tweet the next result stored in links.json.
  --init [search_term]  Create a search terms index at search_terms.json by
                        reading dict.txt. The optional argument determines the
                        word to start building the index from.
  --parse n             Parse n next search terms from search_terms.json for
                        zero view items and store to links.json.
  --random-window       Whether a randomized year long time window should be
                        used when querying Youtube. Affects the -q and --parse
                        switches.
```

## File structure
youtube_search.py
  * The main script.

dict.txt
  * A text file containing words to use as search terms. This file is a slightly modified version of /usr/share/dict/words found on several Linux distributions.

common.txt
  * A list of common english words to use for randomly choosing additional combined search terms

keys.json
  * An empty JSON file to store your Google API key as well as Twitter access tokens and API keys. The main script will attempt to read them from here.

Additionally running the script creates:
search_terms.json
  * An index for single word search terms to use. Upon initialization this is essantially a copy of dict.txt. Further runs of the script will remove items as they are being used.

links.json
  * List of currently stored links to be tweeted.


Written on Python 2.7.8
