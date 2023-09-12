import re
import logging
import orjson
from bs4 import BeautifulSoup
from utils.helper import plex_find_lib, text_format
from services.service import Service


class HamiVideo(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_movie_metadata(self, data):
        title = data['name'].strip()

        movie_synopsis = text_format(
            data['description'].replace('Hami Video', ''))
        movie_poster = data['image']

        content_rating = f"tw/{data['contentRating']}"

        print(f"\n{title}\t{content_rating}\n{movie_synopsis}\n{movie_poster}")

        if not self.print_only:
            movie = plex_find_lib(self.plex, 'movie',
                                  self.plex_title, title)
            movie.edit(**{
                "contentRating.value": content_rating,
                "contentRating.locked": 1,
                "summary.value": movie_synopsis,
                "summary.locked": 1,
            })
            if self.replace_poster:
                movie.uploadPoster(url=movie_poster)

    def main(self):
        res = self.session.get(self.url)
        if res.ok:
            web_content = BeautifulSoup(res.text, 'lxml')

            match = web_content.findAll(
                'script', attrs={'type': 'application/ld+json'})
            if match:
                data = orjson.loads(str(match[0].string))
                if data['@type'] == 'Movie':
                    self.get_movie_metadata(data)
            else:
                self.logger.error("Not found!")
        else:
            self.logger.error(res.text)
