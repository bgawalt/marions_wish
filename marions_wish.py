"""Twitter bots reciting "Marion's Wish"

TODO: Add usage
"""

import sys

from datetime import timedelta
from enum import Enum
from typing import Text, Tuple


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

    def __init__(self, id_: int, sender: Texter, contents: Text, is_img: bool):
        """A single message to be posted to Twitter.

        Args:
            id_: The message's order in the thread.
            texter: Sender of the message.
            contents: Either the text of the message, or an image filename
            is_img: Whether this is image message (or else just text)
        """
        self._id = id_
        self._sender = sender
        self._contents = contents
        self._is_img = is_img

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

    @staticmethod
    def from_line(line: Text, next_id: int) -> 'TextMsg':
        """Parse a line of the script into a text message."""
        sender, contents = Texter.from_line(line)
        id_ = next_id if sender.is_character() else -1
        if sender.is_character() and contents.startswith('IMG '):
            is_img = True
            contents = contents[4:]
        else:
            is_img = False
        return TextMsg(id_=id_, sender=sender, contents=contents, is_img=is_img)


def main(argv):
    # Positional arguments only:
    script_filename = argv[1]
    next_id = 0
    with open(script_filename, 'rt') as infile:
        lines = infile.readlines()
    for line_num, line in enumerate(lines):
        text_msg = TextMsg.from_line(line, next_id)
        if text_msg.sender.is_character():
            next_id += 1
        if text_msg.sender == Texter.UNKNOWN:
            print('UNKNOWN at line', line_num + 1, ":",
                  line[:25].strip(), "...")


if __name__ == "__main__":
    main(sys.argv)
