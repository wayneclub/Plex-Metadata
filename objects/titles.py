from __future__ import annotations
from enum import Enum
import re
import unicodedata

from typing import Any, Iterator, Optional, Union
from unidecode import unidecode
from utils import Logger
from utils.helper import text_format


class Title:
    def __init__(
        self, id_: str, type_: "Title.Types", name: str, year: Optional[int] = None, synopsis: Optional[str] = None, content_rating: Optional[str] = None, poster: Optional[str] = None, background: Optional[str] = None,
        season: Optional[int] = None, season_name: Optional[str] = None, season_synopsis: Optional[str] = None, episode: Optional[int] = None, episode_name: Optional[str] = None,
        episode_synopsis: Optional[str] = None, episode_poster: Optional[str] = None, compress: bool = False, autocrop: bool = False, source: Optional[str] = None, service_data: Optional[Any] = None, extra: Optional[Any] = None
    ) -> None:
        self.id = id_
        self.type = type_
        self.name = name
        self.year = int(year or 0)
        self.synopsis = text_format(synopsis.strip()) if synopsis else ''
        self.content_rating = content_rating
        self.poster = poster
        self.background = background
        self.season = int(season or 0)
        self.season_name = season_name
        self.season_synopsis = text_format(
            season_synopsis.strip()) if season_synopsis else ''
        self.episode = int(episode or 0)
        self.episode_name = text_format(
            episode_name.strip()) if episode_name else ''
        self.episode_synopsis = text_format(
            episode_synopsis.strip()) if episode_synopsis else ''
        self.episode_poster = episode_poster
        self.compress = bool(compress)
        self.autocrop = bool(autocrop)
        self.source = source
        self.service_data: Any = service_data or {}
        self.extra: Any = extra or {}

    def parse_filename(self, folder: bool = False) -> str:
        # create the initial filename string
        # e.g. `Arli$$` -> `ArliSS`
        filename = f"{str(self.name).replace('$', 'S')} "
        if self.type == Title.Types.MOVIE:
            filename += f"{self.year or ''} "
        else:
            if self.season is not None:
                filename += f"S{str(self.season).zfill(2)}"
            if self.episode is None or folder:
                filename += " "  # space after S00
            else:
                filename += f"E{str(self.episode).zfill(2)} "
            if self.episode_name and not folder:
                filename += f"{self.episode_name or ''} "

        # remove whitespace and last right-sided . if needed
        filename = filename.rstrip().rstrip(".")

        return self.normalize_filename(filename)

    @staticmethod
    def normalize_filename(filename: str) -> str:
        # replace all non-ASCII characters with ASCII equivalents
        filename = unidecode(filename)
        filename = "".join(
            c for c in filename if unicodedata.category(c) != "Mn")

        # remove or replace further characters as needed
        # e.g. amazon multi-episode titles
        filename = filename.replace("/", " & ")
        filename = re.sub(r"[:; ]", ".", filename)  # structural chars to .
        filename = re.sub(r"[\\*!?¿,'\"()<>|$#]", "",
                          filename)  # unwanted chars
        # replace 2+ neighbour dots and spaces with .
        filename = re.sub(r"[. ]{2,}", ".", filename)
        return filename

    def is_wanted(self, wanted_season: list, wanted_episode: list) -> bool:
        if self.type != Title.Types.TV or (not wanted_season and not wanted_episode):
            return True
        if not wanted_season or self.season in wanted_season:
            if not wanted_episode or self.episode in wanted_episode:
                return f"{self.season}x{self.episode}"

    class Types(Enum):
        MOVIE = 1
        TV = 2


class Titles(list):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.title_name = None
        if self:
            self.title_name = self[0].name
            self.year = str(self[0].year) if self[0].year > 0 else ''
            self.content_rating = self[0].content_rating
            self.synopsis = self[0].synopsis
            self.poster = self[0].poster

    def print(self) -> None:
        log = Logger.getLogger("Titles")
        log.info(
            f"Title: {self.title_name}{' (' + self.year + ')' if self.year else ''}{' | ' + self.content_rating if self.content_rating else ''}")
        if self.synopsis:
            log.info(self.synopsis)
        if self.poster:
            log.info(self.poster)
        if any(x.type == Title.Types.TV for x in self):
            log.info(f"Total Episodes: {len(self)}")
            log.info(
                "By Season: {}".format(
                    ", ".join(list(dict.fromkeys(
                        f"{x.season} ({len([y for y in self if y.season == x.season])})"
                        for x in self if x.type == Title.Types.TV
                    )))
                )
            )

    def order(self) -> None:
        """This will order the Titles to be oldest first."""
        self.sort(key=lambda t: int(t.year or 0))
        self.sort(key=lambda t: int(t.episode or 0))
        self.sort(key=lambda t: int(t.season or 0))

    def with_wanted(self, download_season: list, download_episode: list) -> Iterator[Title]:
        """Yield only wanted tracks."""
        for title in self:
            if title.is_wanted(download_season, download_episode):
                yield title
