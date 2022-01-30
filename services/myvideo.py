import re
import logging
import orjson
from common.utils import plex_find_lib, text_format
from services.service import Service


class MyVideo(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_show_metadata(self, data, episode_list):

        title = data['name'].strip().replace('預告', '')

        show_synopsis = text_format(
            data['description'].replace(f'《{title}》', ''))
        show_poster = data['image']

        print(f"\n{title}\n{show_synopsis}\n{show_poster}")

        if not self.season_index:
            season_index = 1

        if not self.print_only:
            show = plex_find_lib(self.plex, 'show', self.plex_title, title)
            if season_index == 1:

                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })

                show.season(season_index).edit(**{
                    "title.value": f'第 {season_index} 季',
                    "title.locked": 1,
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })

                if self.replace_poster:
                    show.uploadPoster(url=show_poster)
                    show.season(season_index).uploadPoster(url=show_poster)

        for episode_index, episode in enumerate(episode_list, start=1):

            res = self.session.get(
                f"https://www.myvideo.net.tw/details/0/{episode}")
            if res.ok:
                match = re.findall(r'(\{\"embedUrl\":.+\})', res.text)
                episode_poster = re.findall(
                    r'background-image: url\((.+)\);', res.text)[0]
                if match:
                    episode_data = orjson.loads(match[0])
                    episode_synopsis = text_format(
                        episode_data['description'].replace(f'《{title} 第{episode_index}集》', ''))

                    print(
                        f"\n第 {episode_index} 集\n{episode_synopsis}\n{episode_poster}")

                    if not self.print_only:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": f'第 {episode_index} 集',
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
                        if self.replace_poster:
                            show.season(season_index).episode(
                                episode_index).uploadPoster(url=episode_poster)

    def get_movie_metadata(self, data, rating):
        title = data['name'].strip().replace('預告', '')

        movie_synopsis = text_format(data['description'])
        movie_poster = data['image']

        content_rating = f"tw/{rating}"

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
            match = re.findall(
                r'(\{\"embedUrl\":.+\})', res.text)
            if match:
                data = orjson.loads(match[0])

                if '/details/0/' in self.url or 'seriesType=0' in self.url:
                    rating = re.search(r'"rating": \'(.+)\'', res.text)
                    if rating:
                        content_rating = rating.group(1)
                    self.get_movie_metadata(data, content_rating)
                else:
                    episode_list = re.findall(
                        r"clickVideoHandler\('T','(\d+)'\);", res.text)
                    self.get_show_metadata(data, episode_list)
