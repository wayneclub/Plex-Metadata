import re
import logging
from services.service import Service
from common.utils import plex_find_lib, text_format


class iTunes(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_metadata(self, data):
        title = data['name']
        content_rating = ''
        if 'tw-movies' in data['contentRatingsBySystem'] and data['contentRatingsBySystem']['tw-movies']['name'] != '未經分級':
            content_rating = f"tw/{data['contentRatingsBySystem']['tw-movies']['name']}"
        movie_synopsis = text_format(data['description']['standard'])
        movie_poster = data['artwork']['url'].format(
            w=data['artwork']['width'], h=data['artwork']['height'], f='webp')

        print(f"\n{title}\n{content_rating}\n{movie_synopsis}\n{movie_poster}")

        if not self.print_only:
            movie = plex_find_lib(self.plex, 'movie', self.plex_title, title)
            if content_rating:
                movie.edit(**{
                    "contentRating.value": content_rating,
                    "contentRating.locked": 1,
                    "summary.value": movie_synopsis,
                    "summary.locked": 1,
                })
            else:
                movie.edit(**{
                    "summary.value": movie_synopsis,
                    "summary.locked": 1,
                })

            if self.replace_poster:
                movie.uploadPoster(url=movie_poster)

    def main(self):
        movie_id_regex = re.search(r'\/id(\d+)', self.url)
        movie_id = movie_id_regex.group(1)
        res = self.session.get(f"{self.url}/?isWebExpV2=true&dataOnly=true")
        if res.ok:
            self.get_metadata(
                res.json()['storePlatformData']['product-dv']['results'][movie_id])
