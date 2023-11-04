#!/usr/bin/python3
# coding: utf-8

"""
This module is for service initiation mapping
"""

from constants import Service
from services.amazon import Amazon
from services.appletvplus import AppleTVPlus
from services.disneyplus import DisneyPlus
from services.fridayvideo import FridayVideo
from services.hamivideo import HamiVideo
from services.hbogoasia import HBOGOAsia
from services.iqiyi import IQIYI
from services.kktv import KKTV
from services.myvideo import MyVideo

service_map = [
    {
        'name': Service.Amazon,
        'class': Amazon,
        'domain': 'amazon.com',
    },
    {
        'name': Service.APPLETVPLUS,
        'class': AppleTVPlus,
        'domain': 'tv.apple.com',
    },
    {
        'name': Service.DISNEYPLUS,
        'class': DisneyPlus,
        'domain': 'disneyplus.com'
    },
    {
        'name': Service.FRIDAYVIDEO,
        'class': FridayVideo,
        'domain': 'video.friday.tw'
    },
    {
        'name': Service.HAMIVIDEO,
        'class': HamiVideo,
        'domain': 'hamivideo.hinet.net'
    },
    {
        'name': Service.HBOGOASIA,
        'class': HBOGOAsia,
        'domain': 'hbogoasia'
    },
    {
        'name': Service.IQIYI,
        'class': IQIYI,
        'domain': 'iq.com'
    },
    {
        'name': Service.KKTV,
        'class': KKTV,
        'domain': 'kktv.me'
    },
    {
        'name': Service.MYVIDEO,
        'class': MyVideo,
        'domain': 'myvideo.net.tw'
    }
]
