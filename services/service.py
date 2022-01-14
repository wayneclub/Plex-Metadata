#!/usr/bin/python3
# coding: utf-8

"""
This module is default service
"""
import logging
import requests
from common.utils import connect_plex


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

        self.session = requests.Session()
