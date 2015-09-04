#!/bin/bash
# A launcher script to run youtube_search.py. Attempts to run it again if the
# first try is unsuccessful.

python ./youtube_search.py --bot

ret=$?
if [ $ret -ne 0 ]; then
  echo "Not a valid quote, trying again..."
  python ./youtube_search.py --bot
fi
echo $(date +"%d.%m.%Y-%H:%M")
