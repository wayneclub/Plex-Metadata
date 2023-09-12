import os
import re
import logging
import orjson
from utils.helper import plex_find_lib, text_format
from services.service import Service


class AppleTV(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.api = {
            'movies': 'https://tv.apple.com/api/uts/v3/movies/{movie_id}?utscf=OjAAAAAAAAA~&utsk=6e3013c6d6fae3c2%3A%3A%3A%3A%3A%3A235656c069bb0efb&caller=web&sf=143470&v=58&pfm=web&locale=zh-Hant&l=zh&ctx_brand=tvs.sbd.4000',
            'series': 'https://tv.apple.com/api/uts/v3/shows/{show_id}/episodes?utscf=OjAAAAAAAAA~&utsk=6e3013c6d6fae3c2%3A%3A%3A%3A%3A%3A235656c069bb0efb&caller=web&sf=143470&v=58&pfm=web&locale=zh-Hant&includeSeasonSummary=true&l=zh'
        }

    def get_movie_metadata(self, data):

        title = data['title']

        content_rating = ''
        if data['rating']['displayName'] != '未經分級':
            content_rating = f"tw/{data['rating']['displayName']}"
        movie_synopsis = text_format(data['description'])

        movie_poster = ''
        if 'coverArt' in data['images']:
            movie_poster = data['images']['coverArt']['url'].format(
                w=data['images']['coverArt']['width'], h=data['images']['coverArt']['height'], f='webp')

        movie_background = ''
        if 'centeredFullScreenBackgroundImage' in data['images']:
            movie_background = data['images']['centeredFullScreenBackgroundImage']['url'].format(
                w=4320, h=2160, c='sr', f='webp')
        elif 'previewFrame' in data['images']:
            movie_background = data['images']['previewFrame']['url'].format(
                w=data['images']['previewFrame']['width'], h=data['images']['previewFrame']['height'], c='sr', f='webp')

        print(
            f"\n{title}\t{content_rating}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

        if not self.print_only:
            movie = plex_find_lib(self.plex, 'movie',
                                  self.plex_title, title)

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
                movie.uploadArt(url=movie_background)

    def get_show_metadata(self, data):
        title = data['title']
        show_synopsis = text_format(data['description'])
        show_poster = data['images']['coverArt']['url'].format(
            w=data['images']['coverArt']['width'], h=data['images']['coverArt']['height'], f='webp')
        if 'centeredFullScreenBackgroundImage' in data['images']:
            show_background = data['images']['centeredFullScreenBackgroundImage']['url'].format(
                w=4320, h=2160, c='sr', f='webp')
        else:
            show_background = data['images']['previewFrame']['url'].format(
                w=data['images']['previewFrame']['width'], h=data['images']['previewFrame']['height'], c='sr', f='webp')

        print(
            f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_background}")

        if not self.print_only:
            show = plex_find_lib(self.plex, 'show',
                                 self.plex_title, title)
            show.edit(**{
                "summary.value": show_synopsis,
                "summary.locked": 1,
            })
            if self.replace_poster:
                show.uploadPoster(url=show_poster)
                show.uploadArt(url=show_background)

        res = self.session.get(self.api['episodes'].format(
            show_id=os.path.basename(self.url)))
        if res.ok:
            for episode in res.json()['data']['episodes']:
                season_index = episode['seasonNumber']
                episode_index = episode['episodeNumber']
                episode_title = episode['title']
                episode_synopsis = text_format(episode['description'])
                episode_poster = episode['images']['previewFrame']['url'].format(
                    w=episode['images']['previewFrame']['width'], h=episode['images']['previewFrame']['height'], f='webp')

                print(
                    f"\n第 {season_index} 季 第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_poster}")

                if not self.print_only:
                    if episode_index == 1:
                        if season_index == 1:
                            show.season(season_index).edit(**{
                                "title.value": f'第 {season_index} 季',
                                "title.locked": 1,
                                "summary.value": show_synopsis,
                                "summary.locked": 1,
                            })
                            if self.replace_poster:
                                show.season(season_index).episode(
                                    episode_index).uploadPoster(url=show_poster)
                        else:
                            show.season(season_index).edit(**{
                                "title.value": f'第 {season_index} 季',
                                "title.locked": 1,
                            })
                    show.season(season_index).episode(episode_index).edit(**{
                        "title.value": episode_title,
                        "title.locked": 1,
                        "summary.value": episode_synopsis,
                        "summary.locked": 1,
                    })
                    if self.replace_poster:
                        show.season(season_index).episode(
                            episode_index).uploadPoster(url=episode_poster)

    def main(self):

        res = self.session.get(self.url)
        if res.ok:
            match = re.search(
                r'<script type=\"fastboot\/shoebox\" id=\"shoebox-uts-api\">(.+?)<\/script>', res.text)
            data = orjson.loads(match.group(1).strip())

            id = next(key for key in list(data.keys())
                      if re.sub(r'(.+)\?.+', '\\1.caller.web', os.path.basename(self.url)) in key and 'personalized' not in key)
            print(orjson.loads(data[id])['d']['data'])

            data = orjson.loads(data[id])['d']['data']['content']
            self.logger.debug(data)
            if '/movies/' in self.url:
                self.get_movie_metadata(data)
            else:
                self.get_show_metadata(data)
