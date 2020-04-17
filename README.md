# marions_wish

Bots re-enacting Marion's Wish

This repo powers three twitter accounts:

*  [@tim_mwish](https://twitter.com/tim_mwish)
*  [@gregg_mwish](https://twitter.com/gregg_mwish)
*  [@mark_mwish](https://twitter.com/mark_mwish)

When prompted, they tweet each other, in one long thread, in real time, the
messages found in [**Marion's Wish**](https://marionswish.com).

This repo includes a text-file version of that script, whose special format is
parsed into instructions on which account should tweet, or whether a long pause
is in order.

## Tweetable "Marion's Wish" Script

The text file of the script parses lines of the following format:

*  **Lines that start with `'#'`:** These lines are ignored.  Comments!
*  **Blank lines:** Also ignored
*  **Lines of the format `'Day K, HH:MM XM'`:** Used as instructions on when the
    next block of dialogue should begin ("timelocks"):
      * `K`: Either 0 or 1.  "Marion's Wish" plays out over two days, so this
          encodes whether the dialogue is on the first or second day
      * `HH`: One or two digits for the hour of the day
      * `MM`: Two digits for the minute of the day
      * `XM`: Either AM or PM
*  **Lines that start with `'Tim: '`, `'Gregg: '`, or `'Mark: '`:** These are
    parsed as the actual lines of dialogue to send out.

Any other line encountered will raise a `ValueError`.  The two scripts in this
repo -- `marions_wish.txt` and `test_script.txt` -- both parse just fine.

The Python code parses the script, turning each line of dialogue into a
sender ID and message contents, housed by the class `TextMsg`.  At the same
time, a `TimeKeeper` object will track when timelock lines appear, then make
sure that each `TextMsg` is constructed with the appropriate timelock value
(always in California's time zone).

The full result should look a lot like a group chat thread that grows over the
course of 51 hours.  I have no idea if that's a reasonable ask of a program, to
stay alive but mostly sleeping for that long.

## Config file

At this point, I'm finally convinced that my *next* bot needs to use JSON for
config.  But in the mean time, your config script should be structured as
key-value pairs, mapping strings-to-strings, one pair per line.

Blank lines are okay, comments where the line starts with `'#'` are okay.

Your config should have the following keys:

```python
# Text file containing script for "Marion's Wish"
# Alternate value I use: SCRIPT_FILENAME = test_script.txt
SCRIPT_FILENAME = marions_wish.txt

# Run in test mode?
#  - Ignores the script's timing instructions
#  - Doesn't tweet messages, just `print()`s them
# Set to any string other than 'True' to disable test mode.
TEST_MODE = True

# Delay before tweeting, for self-replies v other
# These *must* parse to integers!
DELAY_SAME_SENDER_SEC = 15
DELAY_DIFF_SENDER_SEC = 40

# App-level OAuth config
CONSUMER_KEY = YourPostingAppsOauthKeyh723kd
CONSUMER_SECRET = YourPostingAppsSecretA834239

# Per-account OAuth configs
TIM_KEY = KeyForTimAccount01029283
TIM_SECRET = SecretForTimAccount

GREGG_KEY = AndSoOn823782374
GREGG_SECRET = AndSoForth3434534

MARK_KEY = MarkTooHeresHisKeyXYAYSDas
MARK_SECRET = AndMarksSecret92334yfsdhds
```

## Dependencies

This code runs in Python 3.7 (.1 on my server, .3 on my laptop).

I installed the following modules with pip into a virtual environment:

```shell
pip install pytz
pip install requests
pip install requests-oauthlib
```

## Notes on timing

Here's a rundown of when big strings of texts start; the number of texts in each
block; and for Day 0 blocks, the time since the start of the thread.

| Time stamp      | Line | Time Elapsed | Num Tweets |
|-----------------|------|--------------|------------|
| Day 0, 7:52 PM  | 64   | --           | 8          |
| Day 0, 8:08 PM  | 72   | 0h 16m       | 12         |
| Day 0, 8:55 PM  | 76   | 1h 3m        | 15         |
| Day 0, 10:01 PM | 79   | 2h 9m        | 21         |
| Day 0, 10:06 PM | 85   | 2h 14m       | 58         |
| Day 0, 10:20 PM | 122  | 2h 28m       | 81         |
| Day 0, 10:48 PM | 145  | 2h 56m       | 163        |
| --              | --   | --           | --         |
| Day 1, 10:39 AM | 227  | --           | 182        |
| Day 1, 10:41 PM | 409  | --           | 103        |
| [the end]       | 512  | --           | --         |

The Twitter API rates limit posts to 300 per 3 hours: 1.6 tweets per minute,
or 36 seconds between each tweet.  I set delays of 30 seconds for
replies-to-self (i.e., if the current sender matches the previous sender),
and 60 seconds otherwise.  Much slower than an actual texting experience, but
what are ya gonna do.

## Future Work

There's some hints in the code that these accounts are supposed to post the
actual images and videos mentioned in the script.  I haven't gotten around to
that, mostly because it don't seem worth it if I don't actually have copies.

I should also force a ~5 minute delay whenever a new timelock is reached, just
to preserve the original spirit of "there was some dead air in the
conversation."  Right now, that can get crowded out with rate-limit delays
piling up.

I'm also not great with timezones, which is not so big a risk factor.  But I
should consider where and how `pytz.normalize` is appropriate with the datetime
arithmetic used here.  Fun read: https://tommikaikkonen.github.io/timezones/
