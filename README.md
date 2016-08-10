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
 * Additionally the Twitterbot feature requires access tokens and keys from Twitter
 https://dev.twitter.com/oauth/overview/application-owner-access-tokens
  * Only required if run with the --bot switch.


## Usage
--init
  * Creates an index file to be used as a source of search terms.

--parse
  * Attempts to read the next batch of search terms from search_terms.json and query them for new YouTube links. Won't do anything if links.json already contains > 9 entries

--tweet
  * Attempts to tweet the topmost entry in links.json. Won't do anything if links.json is empty.

-q [search_term]
  * Perform a sample search on given search term and prints the results on screen. Returns the items with least views.

--empty
  * Empties the contents of links.json but keeps the index intact.

--random window
  * This is an option switch to --parse and -q. This will generate a random time window of one year between one year ago to 1.1.2006 to be used as an additional search parameter to YouTube.


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


## Changelog
8.8.2016
  * Querying: youtube_query() now checks whether the current page is empty and returns the last non-empty page
  * Querying: added common.txt as a source for common multi word search terms
  * Querying: added option to use a random year long time window to narrow done results.
  * Bot behavior: separated parsing new videos from tweeting to --parse and --tweet switches
  * Code cleanup:
    * moved from pickle to json and deleted the --show switch
    * moved some stuff under main to thei own functions for readability
    * command line arguments are now properly parsed before calling main()

3.4.2016
  * Querying: changed paginitaion in youtube_query() to use the API's list_next() method
  * Parsing: zero_search() now parses more than one results per search term (by default, all items in the last page of the results)
  * Parsing: search results with liveContent == "upcoming" are now considered invalid (results to "upcoming" videos that have already occured and can no longer be viewed, maybe find out why this is happening)
  * Maintenance: added an --empty switch for emptying links.pkl

25.2.2016
  * I/O: output is now stored as pickle encoded dicts (links.pkl) instead of a raw csv text file.
  * I/O: added a dynamic index file (search_terms.pkl) to keep track of which words to read next, no more cumbersome byte index method.
  * Code cleanup: the zero search part is now down to 1 function, (zero_search()) and the bot feature is moved directly under main()

16.1.2016
  * Code cleanup: added publishedBefore argument to youtube.search().list()

12.9.2015
  * Initial release


Written on Python 2.7.8
