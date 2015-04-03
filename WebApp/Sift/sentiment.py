from __future__ import absolute_import

import os

try:
    import pymysql
    pymysql.install_as_MySQLdb()

except:
    pass

from django.conf import settings
if not settings.configured:
    settings.configure(
        DATABASES={'default': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': 'restorestemmedbody.cqtoghgwmxut.us-west-2.rds.amazonaws.com',
            'PORT': '3306',
            'USER': 'teamamzn',
            'PASSWORD': 'TeamAmazon2015!',
            'NAME': 'sellerforums',
            'OPTIONS': {
                'autocommit': True,
            },
        }
        }
    )

try:
    from models import Post, Sentiment
except:
    from Sift.models import Post, Sentiment

from lxml import html
import requests
import django
from time import time

django.setup()


def lazy_sentiment(start_date, end_date):
    t0 = time()
    print("grabbing posts from db")
    dataset = Post.objects.all()
    # dataset = Post.objects.filter(creation_date__range=(start_date, end_date))

    suc = 0
    skip = 0
    goto = 47518
    i = 0
    print("lazy sentiment time!")
    for post in dataset:
        i += 1
        print(str(i))
        if i > goto:
            sentimentobj = Sentiment.objects.filter(post_id=post.post_id)
            if sentimentobj.__len__() is 0:
                try:
                    body = html.document_fromstring(post.body).text_content()
                except:
                    body = ""
                payload = {'text': body[:80000]}
                r = requests.post("http://text-processing.com/api/sentiment/", data=payload)
                try:
                    print(payload)
                    print(r.json())
                    senti = Sentiment(post_id=post, prob_negative=r.json()['probability']['neg'],
                                      prob_neutral=r.json()['probability']['neutral'], prob_positive=r.json()['probability']['pos'],
                                      label=r.json()['label'])
                    senti.save()
                    suc += 1
                except:
                    print("broke :(")
                    print(r)
                    if str(r) == "<Response [400]>":
                        print("bad text")
                        senti = Sentiment(post_id=post, prob_negative=0,
                                      prob_neutral=0, prob_positive=0,
                                      label="none")
                        senti.save()
                    else:
                        print("reset ip and launch again")
                        break

            else:
                skip += 1
                print(str(skip) + " skipped")

    print("Successfully sentimented: " + str(suc) + " posts")
    print("Skipped over: " + str(skip) + " posts")
    print("done in %fs" % (time() - t0))



def main():
    lazy_sentiment("2012-01-01", "2014-04-01")



# Only run the main function if this code is called directly
# Not if it's imported as a module
if __name__ == "__main__":
    main()