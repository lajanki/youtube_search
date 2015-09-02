#!/bin/bash

# A launcher script to run the Twitterbot upto 3 times, if the first 2 don't yield
# a successful result.
# Usage:  ./yt_bot.sh

function bot() {
  iter=$1
  python ./youtube_search.py --bot
  ret=$?
  if [ $iter -lt 4 ] && [ $ret -ne 0 ]; then
    echo "No results, trying again..."
    let iter=$iter+1
    bot $iter
  fi
}


bot 1
echo $(date +"%d.%m.%Y-%H:%M")

