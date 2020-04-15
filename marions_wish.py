"""Twitter bots reciting "Marion's Wish"

See README.md for details on config file and text-file-script format.

Usage:
    python marions_wish.py config_file.txt
"""

import pytz
import requests
import sys
import time

from datetime import datetime as dt_datetime
from datetime import time as dt_time
from datetime import timedelta as dt_timedelta
from enum import Enum
from requests_oauthlib import OAuth1
from typing import Dict, Optional, Text, Tuple


_CALI_TZ = pytz.timezone('US/Pacific')

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'


def parse_config(config_filename: Text) -> Dict[Text, Text]:
    with open(config_filename, 'rt') as infile:
        lines = infile.readlines()
    out = {}
    for line in lines:
        if not line.strip():
            continue
        if line.startswith('#'):
            continue
        spline = line.split(' = ', maxsplit=1)
        if len(spline) != 2:
            raise ValueError('Invalid config line! ' + line.strip())
        out[spline[0]] = spline[1].strip()
    return out


# TODO: Naming scheme here collides with typing.Text, rename?
class Texter(Enum):
    """A person sending a text message."""
    # The three characters identified in the script
    TIM = 1
    GREGG = 2
    MARK = 3
    # Error codes for describing non-dialogue script lines
    COMMENT = 4
    BLANK = 5

    def is_character(self):
        return self in {Texter.TIM, Texter.GREGG, Texter.MARK}

    @staticmethod
    def from_line(line: Text) -> Tuple['Texter', Text]:
        """Parses a line of script text and returns a Texter and msg content."""
        if not line.strip():
            return (Texter.BLANK, '')
        if line[0] == '#':
            return (Texter.COMMENT, '')
        spline = line.split(maxsplit=1)
        if len(spline) != 2:
            # This should never happen!
            raise ValueError('Line split failed:', line[:70].strip())
        sender_dict = {
            'Tim:': Texter.TIM,
            'Gregg:': Texter.GREGG,
            'Mark:': Texter.MARK
        }
        if spline[0] not in sender_dict:
            raise ValueError('Unrecognized sender in line:', line[:70].strip())
        return (sender_dict[spline[0]], spline[1])


def create_sender_oauths(config: Dict[Text, Text]) -> Dict[Texter, OAuth1]:
    ckey = config['CONSUMER_KEY']
    csec = config['CONSUMER_SECRET']
    return {
        Texter.TIM: OAuth1(ckey, client_secret=csec,
                           resource_owner_key=config['TIM_KEY'],
                           resource_owner_secret=config['TIM_SECRET']),
        Texter.GREGG: OAuth1(ckey, client_secret=csec,
                             resource_owner_key=config['GREGG_KEY'],
                             resource_owner_secret=config['GREGG_SECRET']),
        Texter.MARK: OAuth1(ckey, client_secret=csec,
                            resource_owner_key=config['MARK_KEY'],
                            resource_owner_secret=config['MARK_SECRET'])
    }


# TODO: Naming scheme here collides with typing.Text, rename?
class TextMsg(object):
    """A text message sent to the thread."""

    def __init__(self, id_: int, sender: Texter, contents: Text, is_img: bool,
                 timelock: dt_datetime):
        """A single message to be posted to Twitter.

        Args:
            id_: The message's order in the thread.
            texter: Sender of the message.
            contents: Either the text of the message, or an image filename
            is_img: Whether this is image message (or else just text)
            timelock: Point in time after which it becomes OK to tweet this
        """
        self._id = id_
        self._sender = sender
        self._contents = contents.strip()
        self._is_img = is_img
        self._timelock = timelock

    @property
    def id(self) -> int:
        return self._id

    @property
    def sender(self) -> Texter:
        return self._sender

    @property
    def contents(self) -> Text:
        return self._contents

    @property
    def is_img(self) -> bool:
        return self._is_img

    @property
    def timelock(self) -> dt_datetime:
        return self._timelock

    @staticmethod
    def from_line(line: Text, next_id: int, timelock: dt_datetime) -> 'TextMsg':
        """Parse a line of the script into a text message."""
        sender, contents = Texter.from_line(line)
        id_ = next_id if sender.is_character() else -1
        if sender.is_character() and contents.startswith('IMG '):
            is_img = True
            contents = contents[4:]
        else:
            is_img = False
        return TextMsg(id_=id_, sender=sender, contents=contents, is_img=is_img,
                       timelock=timelock)


class TimeKeeper(object):
    """Track the time texts take place in the script."""

    def __init__(self, restrict: bool = True):
        now = dt_datetime.now()
        if restrict and now.hour >= 19:
            raise RuntimeError("Can't run this job after 7 PM (Pacific)!!")
        self._day_0 = now.date()
        self._day_1 = self._day_0 + dt_timedelta(days=1)
        self._timelock = dt_datetime.combine(self._day_0, dt_time.min)

    @property
    def timelock(self) -> dt_datetime:
        return self._timelock

    def update_lock(self, line: Text) -> bool:
        """Tries to parse line and update lock, returns True iff success."""
        if line.startswith('Day 0, '):
            day = self._day_0
        elif line.startswith('Day 1, '):
            day = self._day_1
        else:
            return False
        try:
            hour, min_and_period = line[7:].strip().split(':', maxsplit=1)
            min, period = min_and_period.split(' ', maxsplit=1)
            if period == 'AM':
                hour = int(hour)
            elif period == 'PM':
                hour = int(hour) + 12
            else:
                return False
            min = int(min)
            time = dt_time(hour=hour, minute=min)
            self._timelock = _CALI_TZ.localize(dt_datetime.combine(day, time))
        except Exception as e:
            print(e, line[:25])
            return False
        return True


class TweetEmitter(object):
    """Class that handles actually posting to Twitter."""

    def __init__(self, config: Dict[Text, Text]):
        self._test_mode = config['TEST_MODE'] == 'True'
        print('Test mode' if self._test_mode else 'HEADS UP.  LIVE MODE.')
        # Wait a short or long amount of time before tweeting, depending on if
        # the tweet is a self-reply
        self._same_sender_delay_sec = int(config['DELAY_SAME_SENDER_SEC'])
        self._diff_sender_delay_sec = int(config['DELAY_DIFF_SENDER_SEC'])

        # Last tweet added to the thread and its sender
        self._prev_tweet_id = None
        self._prev_sender = None

        self._sender_oauths = create_sender_oauths(config)

    def _wait(self, msg: TextMsg) -> None:
        # Wait different lengths based on whether it's a self-reply:
        if msg.sender == self._prev_sender:
            print('   Same sender delay')
            time.sleep(self._same_sender_delay_sec)
        else:
            print('   Diff sender delay')
            time.sleep(self._diff_sender_delay_sec)
        # Wait for the message's timelock to expire
        now = _CALI_TZ.localize(dt_datetime.now())
        while now < msg.timelock:
            if not self._test_mode:
                print('  Sleep till', msg.timelock)
                time.sleep((msg.timelock - now).total_seconds())
                now = _CALI_TZ.localize(dt_datetime.now())
            else:
                print('  Fake Sleep till', msg.timelock)
                time.sleep(3)
                now = msg.timelock

    def post(self, msg: TextMsg) -> None:
        self._wait(msg)
        def send_tweet(text: Optional[Text], media_id: Optional[Text]) -> Text:
            if text is None and media_id is None:
                raise ValueError('Must supply text or media_id')
            request_data = {
                'status': msg.contents
            }
            if self._prev_tweet_id != None:
                request_data['in_reply_to_status_id'] = self._prev_tweet_id
                request_data['auto_populate_reply_metadata'] = True
            req = requests.post(url=POST_TWEET_URL, data=request_data,
                                auth=self._sender_oauths[msg.sender])
            self._prev_tweet_id = req.json().get('id_str', None)
            print('Successfully posted ', msg.sender, self._prev_tweet_id)

        # TODO: Handle media tweets
        if not self._test_mode:
            send_tweet(msg, None)
        else:
            print(msg.sender, msg.contents)
        self._prev_sender = msg.sender


def main(argv):
    # One positional argument: The config file, which specifies all else.
    config = parse_config(argv[1])
    script_filename = config['SCRIPT_FILENAME']
    next_id = 0

    # TimeKeeper will track timelock values encountered in the script, and
    # apply them to dialogues found in the block following:
    tk = TimeKeeper(restrict=False)
    # TweetEmitter will handle actually respecting the timelocks and pushing
    # the tweets to Twitter:
    emitter = TweetEmitter(config)
    
    print('Initial timelock value:', tk.timelock)
    with open(script_filename, 'rt') as infile:
        lines = infile.readlines()
    msgs = []
    print('Beginning script parse')
    for line_num, line in enumerate(lines):
        if tk.update_lock(line):
            print('New timelock, line', line_num + 1, ':', tk.timelock)
            # No need to try parsing this line as a message, it was timing info
            continue
        text_msg = TextMsg.from_line(line, next_id, tk.timelock)
        if text_msg.sender.is_character():
            next_id += 1
            msgs.append(text_msg)
    print('Parse succeeded.')

    for msg in msgs:
        emitter.post(msg)


if __name__ == "__main__":
    main(sys.argv)
