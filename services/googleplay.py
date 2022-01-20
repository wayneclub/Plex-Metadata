
import logging
import re
import json
from bs4 import BeautifulSoup
from services.service import Service
from common.utils import plex_find_lib, save_html, text_format


class GooglePlay(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_metadata(self, html_page, background_url):
        title = html_page.find('h1').getText(strip=True)
        movie_synopsis = text_format(html_page.find(
            'meta', {'itemprop': 'description'})['content'])

        movie_poster = html_page.find(
            'meta', {'property': 'og:image'})['content'] + '=w2000'

        movie_background = background_url + '=w3840'

        print(
            f"\n{title}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

        if not self.print_only:
            movie = plex_find_lib(self.plex, 'movie',
                                  self.plex_title, title)
            movie.edit(**{
                "summary.value": movie_synopsis,
                "summary.locked": 1,
            })
            if self.replace_poster:
                movie.uploadPoster(url=movie_poster)
                movie.uploadArt(url=movie_background)

    def main(self):
        res = self.session.get(self.url)
        if res.ok:
            match = re.findall(
                r'https:\/\/play-lh\.googleusercontent\.com\/proxy\/[^\"=]+', res.text)
            if match:
                background_url = set(match).pop()
                self.get_metadata(BeautifulSoup(
                    res.text, 'lxml'), background_url)
