#!/usr/bin/python3
# coding: utf-8

"""
This module is default service
"""
from __future__ import annotations
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import Union
import requests
import ssl
from configs.config import user_agent
from objects.titles import Title
from utils import Logger
from cn2an import cn2an
from utils.helper import EpisodesNumbersHandler, connect_plex
from utils.proxy import get_proxy


class BaseService(metaclass=ABCMeta):
    """
    BaseService
    """

    # list of ip regions required to use the service. empty list == global available.
    GEOFENCE: list[str] = []

    def __init__(self, args):
        self.logger = logging.getLogger(__name__)
        self.url = args.url.strip()
        self.source = args.service['name']
        self.movie = False
        self.log = Logger.getLogger(
            self.source,
            level=logging.DEBUG if args.debug else logging.INFO
        )

        self.config = args.config

        self.replace_poster = args.replace_poster
        self.print_only = args.print_only

        if args.season:
            self.download_season = EpisodesNumbersHandler(
                args.season).get_episodes()
        else:
            self.download_season = []

        if args.episode:
            self.download_episode = EpisodesNumbersHandler(
                args.episode).get_episodes()
        else:
            self.download_episode = []

        self.session = requests.Session()
        self.session.mount('https://', TLSAdapter())
        self.session.headers = {
            'user-agent': user_agent
        }

        proxy = args.proxy or next(iter(self.GEOFENCE), None)
        if proxy:
            self.set_proxy(proxy)

    @abstractmethod
    def get_titles(self) -> Union[Title, list[Title]]:
        """
        Get Titles for the provided title ID.

        Return a Title object for every unique piece of content found by the Title ID.
        Each `Title` object should be thought of as one output file/download. E.g. a movie should be one Title,
        and each episode of a TV show would also be one Title, where as a Season would be multiple Title's, one
        per episode.

        Each Title object must contain `title_name` (the Show or Movie name).
        For TV, it also requires `season` and `episode` numbers, with `episode_name` being optional
            but ideally added as well.
        For Movies, it has no further requirements but `year` would ideally be added.

        You can return one Title object, or a List of Title objects.

        For any further data specific to each title that you may need in the later abstract methods,
        add that data to the `service_data` variable which can be of any type or value you wish.

        :return: One of or a List of Title objects.
        """

    def set_proxy(self, proxy):
        """Set proxy: support dynamic proxy in each service"""

        if len("".join(i for i in proxy if not i.isdigit())) == 2:  # e.g. ie, ie12, us1356
            proxy = get_proxy(
                region=proxy, geofence=self.GEOFENCE, platform=self.platform)

        if proxy:
            if "://" not in proxy:
                # assume a https proxy port
                proxy = f"https://{proxy}"
            self.session.proxies.update({"all": proxy})
            self.logger.info(" + Set Proxy")
        else:
            self.logger.info(" + Proxy was skipped as current region matches")

    def get_title_and_season_index(self, title: str) -> tuple(str, int):
        """
        Get title and season_index
        """
        title = title.replace(
            '（', '').replace(
            '）', '').replace(
            '《', '').replace('》', '').replace('(', '').replace(')', '').replace('【', '').replace('】', '').replace('18+', '')

        if re.search(r'[\u4E00-\u9FFF]', title):
            title = title.translate(str.maketrans(
                '０１２３４５６７８９', '0123456789'))
            if '特別篇' in title:
                title = re.search(r'(.+?)(：)*特別篇', title).group(1)
                season_index = 0
            else:
                season_search = re.search(
                    r'(.+?)第(.+?)[季|彈]', title)
                if season_search:
                    title = season_search.group(1)
                    season_index = int(season_search.group(2)) if season_search.group(
                        2).isdigit else int(cn2an(season_search.group(2)))
                else:
                    season_index = re.search(r'(.+?)( )*(\d+)$', title)
                    if season_index:
                        title = season_index.group(1)
                        season_index = int(season_index.group(3))
        else:
            if 'season' in title.lower():
                season_index = re.search(r'(.+?)[s|S]eason( )*(\d+)', title)
                if season_index:
                    title = season_index.group(1)
                    season_index = int(season_index.group(3))
            else:
                season_index = re.search(r'(.+?)[s|S](\d+)', title)
                if season_index:
                    title = season_index.group(1)
                    season_index = int(season_index.group(2))
                else:
                    season_index = re.search(r'(.+?)( )*(\d+)$', title)
                    if season_index:
                        title = season_index.group(1)
                        season_index = int(season_index.group(3))

        if not isinstance(season_index, int):
            season_index = 1

        return title.strip(), season_index


class TLSAdapter(requests.adapters.HTTPAdapter):
    """
    Fix openssl issue
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)
