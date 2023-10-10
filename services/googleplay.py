
import logging
import re
import json
from bs4 import BeautifulSoup
from services.baseservice import BaseService
from utils.helper import get_dynamic_html, plex_find_lib, save_html, text_format


class GooglePlay(BaseService):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_metadata(self, driver):
        html_page = BeautifulSoup(driver.page_source, 'lxml')

        title = html_page.find('h1').getText(strip=True)
        movie_synopsis = text_format(html_page.find(
            'meta', {'property': 'og:description'})['content'])

        movie_poster = html_page.find(
            'meta', {'property': 'og:image'})['content'] + '=w2000'
        match = re.findall(
            r'https:\/\/play-lh\.googleusercontent\.com\/proxy\/[^\"=]+', driver.page_source)

        movie_background = ''
        if match:
            movie_background = set(match).pop() + '=w3840'

        print(
            f"\n{title}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

        driver.quit()

        if not self.print_only:
            movie = plex_find_lib(self.plex, 'movie',
                                  self.plex_title, title)
            movie.edit(**{
                "summary.value": movie_synopsis,
                "summary.locked": 1,
            })
            if self.replace_poster:
                movie.uploadPoster(url=movie_poster)
                if movie_background:
                    movie.uploadArt(url=movie_background)

    def main(self):
        driver = get_dynamic_html(self.url)
        self.get_metadata(driver)
