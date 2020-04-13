"""Twitter bots reciting "Marion's Wish"

TODO: Describe config file

Usage:
    python marions_wish.py config_file.txt
"""

import pytz
import sys
import time

from datetime import datetime as dt_datetime
from datetime import time as dt_time
from datetime import timedelta as dt_timedelta
from enum import Enum
from requests_oauthlib import OAuth1
from typing import Dict, Text, Tuple


_CALI_TZ = pytz.timezone('US/Pacific')


def parse_config(config_filename: Text) -> Dict[Text, Text]:
    with open(config_filename, 'rt') as infile:
        lines = infile.readlines()
    out = {}
    for line in lines:
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
    # TODO: consider dropping this one and just throwing exception instead.
    UNKNOWN = 6

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
            return (Texter.UNKNOWN, 'max_split fail! ' + line)
        sender = {'Tim:': Texter.TIM,
                  'Gregg:': Texter.GREGG,
                  'Mark:': Texter.MARK}.get(spline[0], Texter.UNKNOWN)
        return (sender, spline[1])


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

    def __init__(self, config: Dict[Text, Text], test_mode: bool = False):
        self._test_mode = test_mode
        # How long to wait before letting the same account tweet again.
        self._same_sender_delta = dt_timedelta(seconds=(6 if test_mode else 60))
        # How logn to wait after posting no matter who's posting next.
        self._post_delay_sec = 3 if test_mode else 30

        # Last tweet added to the thread
        self._prev_tweet_id = None

        now = _CALI_TZ.localize(dt_datetime.now())
        self._sender_timelocks = {
            Texter.TIM: now,
            Texter.GREGG: now,
            Texter.MARK: now
        }

        ckey = config['CONSUMER_KEY']
        csec = config['CONSUMER_SECRET']
        self._sender_oauths = {
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

    def _wait(self, msg: TextMsg) -> None:
        now = _CALI_TZ.localize(dt_datetime.now())
        sender_timelock = self._sender_timelocks[msg.sender]
        while now < sender_timelock:
            time.sleep((sender_timelock - now).total_seconds())
            now = _CALI_TZ.localize(dt_datetime.now())
        now = _CALI_TZ.localize(dt_datetime.now())
        while now < msg.timelock:
            if not self._test_mode:
                time.sleep((msg.timelock - now).total_seconds())
                now = _CALI_TZ.localize(dt_datetime.now())
            else:
                print('Fake-sleeping for %d seconds' %
                      ((msg.timelock - now).total_seconds(),))
                time.sleep(3)
                now = msg.timelock

    def post(self, msg: TextMsg) -> None:
        self._wait(msg)
        print('POST!! ', msg.sender, msg.contents[:50])
        self._sender_timelocks[msg.sender] = (
            _CALI_TZ.localize(dt_datetime.now()) + self._same_sender_delta)
        print('  new timelock for', msg.sender, ':',
              self._sender_timelocks[msg.sender])
        time.sleep(self._post_delay_sec)


def main(argv):
    # One positional argument: The config file, which specifies all else.
    config = parse_config(argv[1])
    script_filename = config['SCRIPT_FILENAME']
    next_id = 0
    tk = TimeKeeper(restrict=False)
    emitter = TweetEmitter(config, test_mode=True)
    print('Initial timelock value:', tk.timelock)
    with open(script_filename, 'rt') as infile:
        lines = infile.readlines()
    msgs = []
    for line_num, line in enumerate(lines):
        if tk.update_lock(line):
            print('New timelock:', tk.timelock)
            # No need to try parsing this line as a message, it was timing info
            continue
        text_msg = TextMsg.from_line(line, next_id, tk.timelock)
        if text_msg.sender.is_character():
            next_id += 1
            msgs.append(text_msg)
        if text_msg.sender == Texter.UNKNOWN:
            print('UNKNOWN at line', line_num + 1, ":",
                  line[:25].strip(), "...")

    for msg in msgs:
        emitter.post(msg)


if __name__ == "__main__":
    main(sys.argv)
