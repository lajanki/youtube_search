#!/bin/bash
# A launcher script to run quote.py. Attempts to run it again if the
# first try is unsuccessful.

python ./youtube_search.py --bot

ret=$?
if [ $ret -ne 0 ]; then
  echo "bot.sh: trying again..."
  python ./youtube_search.py --bot
fi
echo $(date +"%d.%m.%Y-%H:%M")
