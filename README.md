# youtube_search
A twitterbot tweeting links to YouTube videos with no views.

The Google YouTube Data API comes with certain restrictions that prevents from directly searching for content with no views. Namely:
 1. view count is not a valid search parameter, and
 2. any search query will return at most 500 results.

This script uses a brute force type approach by performing a search on a number of randomly chosen search terms and stores the results with zero views to a database. The fraction of videos with no views from all query responses is usually small. It is therefore recommended to choose a large search term batch size when running the script.

The search terms are read from a text file containing common English language words.
To limit the possibility of the same search term returning the same results on a subsequent search, a random time frame
is generated for each API query.

## Requirements
Install a virtualenv and Python dependencies with
```
python3 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

To run the script you need API keys for YouTube and Twitter:
 * https://developers.google.com/api-client-library/python/guide/aaa_apikeys
   * Choose to create an `API key` and not a `service account key`
 *  https://dev.twitter.com/oauth/overview/application-owner-access-tokens
Copy all keys to their appropriate places in `keys.json`.



## Usage
The two run scripts `run_search.py`and `run_bot.py` can be used to perform a sample search and to run the actual Twitter bot.

To perform a sample search using a random batch of `n` search terms from `common.txt` run
```
python run_search.py n
```
Due to the API search restrictions above a single query using a random search term has a low chance of providing valid results. Therefore a large value of `n > 40` is recommended. Zero view results are lsited on screen.


To run the bot, first initialize it with
```
python run_bot.py --init
```
This creates a database for storing search terms and links to zero view videos. Next, parse for zero view videos with
```
python run_bot.py --parse n
```
This uses `n` random search terms from the database and stores valid results.

Finally tweet an item from the database with
```
python run_bot.py --tweet
```

The full interface to the bot is
```
Tweets links to YouTube videos with no views.

optional arguments:
  -h, --help            show this help message and exit
  --tweet               Tweet the next result stored in the database
  --parse n             Choose n random search terms from the database and
                        parse for zero view videos. Stores valid links to the
                        database.
  --parse-if-low n threshold
                        Parse new links if less than threshold links left in
                        the database
  --status               Displays the number of links and search terms left in
                        the database.
  --init                Initialize the bot by creating a file structure in
                        bot-data/
```


### Unit tests
Unit tests can be run with
```
python -m unittest tests/*.py
```