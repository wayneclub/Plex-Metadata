
from __future__ import annotations
from configs.config import config
from utils import Logger
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount


class Plex(object):
    """
    BaseService
    """

    def __init__(self):
        self.plex = self.connect_plex()

    def connect_plex(self):
        """Connect Plex"""
        log.info(" + Connect to plex server")
        if config.plex['baseurl'] and config.plex['token']:
            return PlexServer(config.plex['baseurl'], config.plex['token'])
        elif config.plex['username'] and config.plex['password'] and config.plex['servername']:
            account = MyPlexAccount(
                config.plex['username'], config.plex['password'])
            return account.resource(config.plex['servername']).connect()

        log.exit(" - Unable to connect to plex server!")

    def plex_find_lib(self, lib_type: str, plex_title: str = "", title: str = ""):
        """Find plex library"""

        if plex_title:
            lib = self.plex.library.search(title=plex_title, libtype=lib_type)
        else:
            lib = self.plex.library.search(title=title, libtype=lib_type)
            if not lib:
                title = input("請輸入正確標題：")
                lib = self.plex.library.search(title=title, libtype=lib_type)

        if len(lib) > 1:
            for index, data in enumerate(lib):
                log.info(
                    f"{index}: {data.title} ({data.year}) [{data.ratingKey}]")

            correct_index = int(input("請選擇要改的編號："))
            lib = lib[correct_index]
        elif len(lib) == 1:
            lib = lib[0]
        else:
            log.exit(f"plex找不到{title}，請附上正確標題")

        return lib


if __name__:
    log = Logger.getLogger("Plex")
