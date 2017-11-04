# youtube_search
A script for finding YouTube videos with no views.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. view count is not a valid search parameter, and
  2. any search query will return at most 500 results.

This script uses a brute force type approach by performing a search on a
bunch of search terms and stores the results with zero views to an sqlite database.

The search terms are read from two source files:
  * dict.txt, containing > 71 000 individual words. Words read here are processed in groups of n files at a time.
  * common.txt, containing > 20 000 common English words. This file is used to generate additional random k-word search terms.

There are two ways to run this script:
  * ```main.py``` for listing the results on stdout. This is mainly for demonstration purposes. Requires Google API key, see below
  * ```twitterbot.py``` poviding the option to tweet detected zero view items. Requires Google and Twitter API keys.


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
Run
```
python main.py --search n
```
to perform a sample search on n random search terms. Any detected zero view videos are listed on screen.
Due to the restrictions listed above you may find that you need to do the parsing with values n>100 to find any valid results.

Similarly,  to use the bot, first initialize it with
```
python twitterbot.py --init
```
This creates a database with an index of search terms and a table for zero view links. To parse for zero view items, run
```
python twitterbot.py --parse n
```
This takes n/2 random words from the index, generates another n/2 from ```common.txt``` and performs a search. Valid links are stored to the database.

To tweet a randomly chosen link from the database, run
```
python twitterbot.py --tweet
```
Before tweeting the link, an additional check takes palce to ensure the video hasn't gained any views since it was inserted into the database.
