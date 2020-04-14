"""Delete test tweets.

Stock DELETE_ME a list of Tuple[Texter, Text] where the Text element is an ID
of a tweet (owned by the Texter) you want deleted.

Use the same config file as marions_wish.py

Usage:
    python delete_em.py config.txt
"""

import requests
import sys
import time

from marions_wish import create_sender_oauths, parse_config

from marions_wish import Texter
from requests_oauthlib import OAuth1


DELETE_ME = [
    (Texter.TIM, '1249944035772354561'),
    (Texter.GREGG, '1249944049072476160'),
    (Texter.MARK, '1249944062288752640'),
    (Texter.TIM, '1249944093666316288'),
    (Texter.TIM, '1249944169113477121'),
    (Texter.GREGG, '1249944194929405952')
]


def main(argv):
    config = parse_config(argv[1])
    oauths = create_sender_oauths(config)
    for sender, tweet_id_str in DELETE_ME:
        print('Attempting', sender, tweet_id_str)
        resp = requests.post(
            url=("https://api.twitter.com/1.1/statuses/destroy/%s.json" %
                 (tweet_id_str,)),
            auth=oauths[sender])
        print('    deleted', resp.json().get('id_str', None))
        time.sleep(10)


if __name__ == "__main__":
    main(sys.argv)
