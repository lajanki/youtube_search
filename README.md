# youtube_search
A Python script that searches for YouTube videos with no views (by default).

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and
  2. any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
bunch of search terms and saves the results with zero views to a buffer file.
Each time this script is run either the topmost link will be read from the file or,
if the file is empty, new links will be generated.

The search terms are read from a dictionary file consisting of > 71 000 words.
These words are read in groups of 50.


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
First, initialize the script with python youtube_search.py  --init. This creates an index file to be used as a source of search terms.

python youtube_search.py  --bot
  * Prints and tweets the next link from the buffer file, or creates new links if the file is empty.

python youtube_search.py -q [search_term]
  * Performs a YouTube search using either a random search term (no search term provided) or search_term. Prints the result on screen, does not tweet. This option is for sample run purposes, it returns a result having the least views within the API's restrictions. May not results to a zero view item.

python youtube_search.py --show
  * Shows contents of the currently stored links to be tweeted.

python youtube_search.py --empty
  * Empties the contents of links.pkl but keeps the index intact.


## File structure
youtube_search.py
  * The main script.

dict.txt
  * A text file containing all possible search terms. This file is a slightly modified version of /usr/share/dict/words found on several Linux distributions. 

keys.json
  * An empty JSON file to store your Google API key as well as Twitter access tokens and API keys. The main script will attempt to read them from here.

Additionally running the script creates:
search_terms.pkl
  * A dynamically changing source of search terms to use. Upon initialization this is essantially a copy of dict.txt. Further runs of the script will remove items as they are being used.

links.pkl
  * The buffer of currently stored links ready to be tweeted. Once this file is empty, the next run of the scripts creates new ones.


## Changelog
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
