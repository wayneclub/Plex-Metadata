#!/usr/bin/python3
# coding: utf-8

"""
This module is default service
"""
import logging
import requests
from configs.config import Config
from utils.helper import connect_plex


class Service(object):
    def __init__(self, args):
        self.logger = logging.getLogger(__name__)
        self.url = args.url.strip()

        self.plex_title = args.title
        self.replace_poster = args.replace_poster
        self.print_only = args.print_only

        if args.season_index:
            self.season_index = int(args.season_index)
        else:
            self.season_index = None

        if not self.print_only:
            self.plex = connect_plex()
        else:
            self.plex = None

        self.config = Config()
        self.session = requests.Session()
        self.user_agent = self.config.get_user_agent()
        self.session.headers = {
            'user-agent': self.user_agent
        }

        self.ip_info = args.proxy
        self.proxy = self.ip_info['proxy']
        if self.proxy:
            self.session.proxies.update(self.proxy)
            self.proxy = list(self.proxy.values())[0]
        else:
            self.proxy = ''

        if args.region:
            self.region = args.region.upper()
        else:
            self.region = self.ip_info['country']

        self.download_path = self.config.paths()['downloads']
