from __future__ import annotations
from enum import Enum
from typing import Any, Iterator, Optional, Union
from utils import Logger
from utils.helper import text_format


class Title:
    def __init__(
        self, id_: str, type_: "Title.Types", name: str, year: Optional[int] = None, synopsis: Optional[str] = None, poster: Optional[str] = None, content_rating: Optional[str] = None,
        season: Optional[int] = None, season_name: Optional[str] = None, season_synopsis: Optional[str] = None, episode: Optional[int] = None, episode_name: Optional[str] = None,
        episode_synopsis: Optional[str] = None, episode_poster: Optional[str] = None, source: Optional[str] = None, service_data: Optional[Any] = None
    ) -> None:
        self.id = id_
        self.type = type_
        self.name = name
        self.year = int(year or 0)
        self.synopsis = text_format(synopsis.strip()) if synopsis else ''
        self.content_rating = content_rating
        self.poster = poster
        self.season = int(season or 0)
        self.season_name = season_name
        self.season_synopsis = text_format(season_synopsis.strip()) if season_synopsis else ''
        self.episode = int(episode or 0)
        self.episode_name = text_format(episode_name.strip()) if episode_name else ''
        self.episode_synopsis =  text_format(episode_synopsis.strip()) if episode_synopsis else ''
        self.episode_poster = episode_poster
        self.source = source
        self.service_data: Any = service_data or {}

    def is_wanted(self, wanted_season: list, wanted_episode:list) -> bool:
        if self.type != Title.Types.TV or (not wanted_season and not wanted_episode):
            return True
        if not wanted_season or self.season in wanted_episode:
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
            self.content_rating = self[0].content_rating
            self.synopsis = self[0].synopsis
            self.poster = self[0].poster

    def print(self) -> None:
        log = Logger.getLogger("Titles")
        log.info(f"Title: {self.title_name}{' | ' + self.content_rating if self.content_rating else ''}")
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
