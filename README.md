# youtube_search
A script for finding YouTube videos with no views.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and
  2. any search query will return at most 500 results.

This script uses a brute force type approach by performing the search to a
bunch of search terms and records the results with zero views.

The search terms are read from two source files:
  * dict.txt, containing > 71 000 individual words. Words read here are processed in groups of n files at a time.
  * common.txt, containing > 20 000 common English words. This file is used to generate additional random k-word search terms.

There are two ways to run this script:
  * ```main.py``` for listing the results on stdout. This is mainly for demonstration purposes. Requires Google API key, see below
  * ```twitterbot.py``` poviding the option to tweet detected zero view items. This also requires Twitter keys.


## Requirements
##### Modules
* Google APIs Client Library:
  https://developers.google.com/api-client-library/python/start/installation
* Twython:
https://twython.readthedocs.org/en/latest/

##### Keys:
 * Google API Key:
https://developers.google.com/api-client-library/python/guide/aaa_apikeys
 * Additionally the bot feature requires access tokens and keys from Twitter
 https://dev.twitter.com/oauth/overview/application-owner-access-tokens
Both keys should be stored in ```keys.json```.


## Usage
The main script main.py supports the following switches
```
--init      Create a search term index file by processing dict.txt.
--parse n   Parse n search terms from the index for zero views and list valid item on screen.
```
Due to the restrictions listed above you may find that you need to do the parsing with values n>100 to find any valid results.

Similarly,  to use the bot, first initialize it by
```
python twitterbot.py --init
```
This creates a new folder and initializes it with a search term index and a link storage files. To parse for zero view items, run
```
python twitterbot.py --parse n
```
This takes n/2 random words from the index, performs a search and stores results with no views to links.json. Another n/2 search terms are randomly generated from combining two common words in common.txt.

To tweet the topmost result in the link storage, run
```
python twitterbot.py --tweet
```
