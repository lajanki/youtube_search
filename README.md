# youtube_search
A Python script that attempts to find old YouTube videos with little or no vews.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and                             
  2. any search query will return at most 500 results.
Instead this script uses a random search term, orders the results by view count and chooses the last result.

Additioanlly a radom week long timeframe from one year ago to three years ago is specified as search parameter to narrow the results. 

This script does not make any guarantees about the outcome: you may not get any result at all or the result may already have several views. There are also no guarantees about the same result showing up later, though there are more than 71 000 search terms and 104 weeks to choose from.


---
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

---
## Usage
python youtube_search.py  
  * Chooses a random search term and a weeklong timeframe. Performs the search and outputs the least viewed result. Prints title, YouTube video link, view count and published date.

python youtube_search.py --bot
  * Also tweets the result.

---
## File structure
youtube_search.py
  * The main script

dict.txt
  * A text file containing all possible search terms. One is randomly chosen on each time the script is run. This file modified from /usr/share/dict/words found on several Linux distributions. 

keys.json
  * An empty JSON file to store your Google API key as well as Twitter access tokens and API keys. The main script will attempt to read them from here.

bot.sh
  * A Linux shell script to launch the main script with the --bot switch. Runs it again if the first try is unsuccessful.



Written on Python 2.7.8  
Lauri Ajanki 31.8.2015
