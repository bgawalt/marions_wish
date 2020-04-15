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

GREGG_KEY = AndSoOn
GREGG_SECRET = AndSoForth

MARK_KEY = MarkTooHeresHisKey
MARK_SECRET = AndMarksSecret92334yfsdhds
```

## Dependencies

```shell
pip install pytz
pip install requests
pip install requests-oauthlib
```
