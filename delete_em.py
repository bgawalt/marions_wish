"""Delete test tweets.

Stock DELETE_ME a list of Tuple[Texter, Text] where the Text element is an ID
of a tweet (owned by the Texter) you want deleted.

Use the same config file as marions_wish.py

Usage:
    python delete_em.py config.txt
"""

import json
import requests
import sys
import time

from marions_wish import create_sender_oauths, parse_config

from marions_wish import Texter
from requests_oauthlib import OAuth1


DELETE_ME = [
    (Texter.MARK, '1249944062288752640'),
    (Texter.TIM, '1250304056012066819'),
    (Texter.GREGG, '1250304073464557569')
]


def main(argv):
    config = parse_config(argv[1])
    oauths = create_sender_oauths(config)
    for sender, tweet_id_str in DELETE_ME:
        print('\nAttempting', sender, tweet_id_str)
        resp = requests.post(
            url=('https://api.twitter.com/1.1/statuses/destroy/%s.json' %
                 (tweet_id_str,)),
            auth=oauths[sender])
        if 'id_str' in resp.json():
            print('   delete succeeded')
        else:
            print('FAILURE!')
            print(json.dumps(resp.json(), indent=2))
        time.sleep(10)


if __name__ == "__main__":
    main(sys.argv)
