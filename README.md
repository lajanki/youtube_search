# youtube_search
A Python script that searches for YouTube videos with no or little (<10) views.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and                             
  2. any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
bunch of search terms and saves the results with <10 views to a buffer file.
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
python youtube_search.py  --bot
  * Prints and tweets the next link from the buffer file, or creates new links if the file is empty.

python youtube_search.py -q [search_term]
  * Performs a YouTube search on either a random search term (no search term provided) or on search_term. Prints the result on screen, does not tweet. The printed result is a dictionary object containing the title,  url, view count and upload date. This option does not make any guarentees about the view count.


## File structure
youtube_search.py
  * The main script.

dict.txt
  * A text file containing all possible search terms. This file modified from /usr/share/dict/words found on several Linux distributions. 

keys.json
  * An empty JSON file to store your Google API key as well as Twitter access tokens and API keys. The main script will attempt to read them from here.

Additionally running the script will create links.dat
  * A comma seperated text file containing  the serch term, url, view count and upload date of videos with <10 views filtered from the previosly parsed 50 word segment of dict.txt. 



Written on Python 2.7.8  
Lauri Ajanki 12.9.2015
