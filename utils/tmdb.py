from urllib.parse import quote

import requests
from configs import config
from utils import Logger


class tmdb:
    """
    TMDB v3 api (https://developer.themoviedb.org/reference/intro/getting-started).
    """

    def __init__(self):
        self.log = Logger.getLogger("TMDB")
        self.api_key = config.tmdb.get('api_key')
        if not self.api_key:
            self.log.exit(
                "Please get tmdb api key and set in video_downloader.toml!")

    def get_title(self, title: str, release_year: str = "", is_movie: bool = False) -> dict:
        """
        Get tmdb information.
        """
        url = f"https://api.themoviedb.org/3/search/{'movie' if is_movie else 'tv'}?query={quote(title)}"
        if release_year:
            url += f"&{'primary_release_year' if is_movie else 'first_air_date_year'}={release_year}"
        url += f"&api_key={self.api_key}"
        res = requests.get(
            url, headers={'User-Agent': config.user_agent}, timeout=10)
        if res.ok:
            return res.json()
        self.log.exit(res.text)

    def get_episodes(self, series_id: str) -> dict:
        """
        Get series episodes
        """
        url = f"https://api.themoviedb.org/3/tv/{series_id}?api_key={self.api_key}"
        res = requests.get(
            url, headers={'User-Agent': config.user_agent}, timeout=1)
        if res.ok:
            return res.json()
        self.log.exit(res.text)
