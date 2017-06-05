#!/usr/bin/python
# -*- coding:utf-8 -*-

#계정 정보는 외부파일로 빼놓음
import credentials
from updater import update_timeline

# 알라딘 전체 카테고리 ID는 http://image.aladin.co.kr/img/files/aladin_Category_CID_20161011.xls 를 참조
ALADIN_CATEGORY_ID_COMICS = '2551'
ALADIN_CATEGORY_ID_LNOVEL = '50927'
ALADIN_CATEGORY_ID_ITBOOK = '351'

if __name__ == '__main__':
    update_timeline(ALADIN_CATEGORY_ID_COMICS, credentials.TWITTER_AUTH_COMICS,
                    credentials.ALADIN_TTB_KEY, credentials.ALADIN_PARTNER_ID)
    update_timeline(ALADIN_CATEGORY_ID_LNOVEL, credentials.TWITTER_AUTH_LNOVEL,
                    credentials.ALADIN_TTB_KEY, credentials.ALADIN_PARTNER_ID)
    update_timeline(ALADIN_CATEGORY_ID_ITBOOK, credentials.TWITTER_AUTH_ITBOOK,
                    credentials.ALADIN_TTB_KEY, credentials.ALADIN_PARTNER_ID)
