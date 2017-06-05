#!/usr/bin/python
# -*- coding:utf-8 -*-

import os
import os.path
import logging
import logging.handlers
import sqlite3
import tweepy
import requests

from six.moves.urllib.request import urlretrieve
from six.moves.urllib.parse import urlencode


DB_FILENAME = 'aladin.db'
LOG_FILENAME = 'aladin.log'
ALADIN_ITEM_ENDPOINT = 'http://www.aladin.co.kr/ttb/api/itemlist.aspx'


class TwitterAuth:
    """트위터 인증용 클래스"""
    def __init__(self, consumer_key, consumer_secret, access_token, token_secret):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.token_secret = token_secret

    def get_oauth_handler(self):
        """OAuthHandler 작성"""
        auth_handler = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth_handler.set_access_token(self.access_token, self.token_secret)
        return auth_handler


def make_url(category_id, ttb_key, partner_id, start, limit):
    """요청 URL 작성"""
    query = dict()
    query['querytype'] = 'itemnewall'
    query['searchtarget'] = 'book'
    query['version'] = '20131101'
    query['cover'] = 'big'
    query['output'] = 'js'
    query['categoryid'] = category_id
    query['ttbkey'] = ttb_key
    query['start'] = start
    query['maxresults'] = limit
    query['optresult'] = 'ebooklist'
    if partner_id:
        query['partner'] = partner_id
    query_string = urlencode(query)
    return ALADIN_ITEM_ENDPOINT + '?' + query_string


def normalize_link(link):
    """링크 수정"""
    return link.replace('\\/', '/').replace('&amp;', '&')


def make_status(title, info, link):
    """트윗할 수 있게 타이틀의 사이즈를 줄임"""
    # 트위터는 140자까지이나, 링크가 23자를 차지하므로 117까지 계산해서 카운트한다.
    status = title + info
    if len(status) > 117:
        rest_count = 117 - len(info)
        status = title[:rest_count-1] + '…' + info
    return status + link


def create_db_if_not_exist(connection, cursor):
    """테이블이 없으면 생성"""
    table_create_query = '''
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            publisher TEXT,
            link TEXT,
            img_src TEXT,
            isbn TEXT
        )'''
    cursor.execute(table_create_query)
    if cursor.rowcount != -1:
        connection.commit()


def update_timeline(category_id, ttb_key, auth, partner_id='', start=1, limit=30):
    """타임라인 업데이트"""
    query_url = make_url(category_id, ttb_key, partner_id, start, limit)
    response = requests.get(query_url)
    if response.status_code == 200:
        res = response.json()

        if res['totalResults'] > 0:
            curdir = os.path.dirname(__file__)

            # 로거
            logfile_path = os.path.join(curdir, LOG_FILENAME)
            logfile_size = 1024 * 1024 * 4
            formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
            handler = logging.handlers.RotatingFileHandler(logfile_path, 'a', logfile_size, 8)
            handler.setFormatter(formatter)
            logger = logging.getLogger(__name__)
            logger.addHandler(handler)

            db = None
            try:
                db = sqlite3.connect(curdir + '/' + DB_FILENAME)
                cursor = db.cursor()
                create_db_if_not_exist(db, cursor)

                twitter_api = tweepy.API(auth.get_oauth_handler())

                for entity in res['item']:
                    # DB에 정보가 없을때에만 갱신.
                    cursor.execute('SELECT COUNT(*) FROM books WHERE id=?', (entity['itemId'],))
                    row = cursor.fetchone()

                    if row[0] == 0:
                        title = entity['title']
                        link = normalize_link(entity['link'])
                        cover = entity['cover']

                        # 이미지 소스를 받아옴
                        img_file = None
                        if cover is not None:
                            filename = os.path.basename(cover)
                            f = urlretrieve(cover, filename)
                            img_file = f[0]

                        # 트윗
                        try:
                            media_ids = None
                            if img_file is not None:
                                media_status = twitter_api.media_upload(filename=img_file)
                                # 이미지 파일은 하나뿐이므로 튜플이나 리스트로 만들어둬야 tweepy 내에서 오류가 생기지 않음
                                media_ids = (media_status.media_id,)

                            additional_info = u' ({0} / {1} / {2} / {3}원) '.format(entity['author'], entity['publisher'], entity['pubDate'], entity['priceStandard'])
                            status = make_status(title, additional_info, link)
                            update_status = twitter_api.update_status(status=status, media_ids=media_ids)

                            # 전자책 정보가 있을때는 한번 더 연결
                            if entity['subInfo']['ebookList']:
                                ebook_info = entity['subInfo']['ebookList'][0]
                                title = u'[eBook] ' + title
                                additional_info = u' ({0}원) '.format(ebook_info['priceSales'])
                                link = normalize_link(ebook_info['link'])
                                status = make_status(title, additional_info, link)
                                twitter_api.update_status(status=status, in_reply_to_status_id=update_status.id, media_ids=media_ids)

                        except tweepy.error.TweepError as e:
                            logger.error('%s - %s', title, e)
                            continue

                        finally:
                            if img_file is not None:
                                os.remove(img_file)
                                img_file = None

                        # DB에 추가
                        info = (entity['itemId'], entity['title'], entity['author'], entity['publisher'], link, cover, entity['isbn13'])
                        cursor.execute('INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?)', info)
                        db.commit()


            except sqlite3.Error as e:
                if db is not None:
                    db.rollback()
                logger.error(e)

            finally:
                if db is not None:
                    db.close()
