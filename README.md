# youtube_search
A script that attempts to find old YouTube videos with little or no vews.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
  1. one cannot use view count as a search parameter, and                             
  2. any search query will return at most 500 results.
Instead this script uses a random search term, orders the results by view count and chooses the last result.

Additioanlly a radom week long timeframe from one year ago to three years ago is specified as search parameter to narrow the results. 

This script does not make any guarantees about the outcome: the results may have zero or several views or, with a bad search term, no results at all.

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
 * Additionally the Twitter bot-feature requires access tokens and keys from Twitter
 https://dev.twitter.com/oauth/overview/application-owner-access-tokens

## Usage


Lauri Ajanki 31.8.2015
