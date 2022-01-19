import logging
import re
from urllib.request import DataHandler
import orjson
from urllib.parse import urlsplit
from common.utils import get_static_html, plex_find_lib, text_format, save_html
from services.service import Service


class PrimeVideo(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.api = {
            'season': 'https://www.amazon.com/-/zh_TW/gp/video/detail/{season_key}/ref=atv_dp_season_select_s{season_index}?language=zh_TW'
        }

    def get_metadata(self, data):
        save_html(data)
        title_id = data['pageTitleId']
        title_info = data['detail']['headerDetail'][title_id]
        title = title_info['title']
        if title_info['entityType'] == 'TV Show':
            show_synopsis = text_format(title_info['synopsis'])

            print(f"\n{title}\n{show_synopsis}")

            if not self.print_only:
                show = plex_find_lib(self.plex, 'show', self.plex_title, title)
                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })

            for season in data['seasons'][title_id]:
                season_url = f"https://{urlsplit(self.url).netloc}{season['seasonLink']}?language=zh_TW"
                self.logger.debug(season_url)
                season_id = season['seasonId']

                res = self.session.get(season_url)

                if res.ok:
                    match = re.findall(
                        r'<script type=\"text/template\">(\{\"props\":\{\"state\".+)</script>', res.text)
                    if match:
                        season_data = orjson.loads(match[-1])['props']['state']

                        season_title_info = season_data['detail']['btfMoreDetails'][season_id]

                        season_index = season_title_info['seasonNumber']
                        season_title = f'第 {season_index} 季'
                        season_synopsis = text_format(
                            season_title_info['synopsis'])
                        season_background = season_title_info['images']['heroshot']

                        print(
                            f"\n{season_title}\n{season_synopsis}\n{season_background}")

                        if season_index and not self.print_only:
                            show.season(season_index).edit(**{
                                "title.value": season_title,
                                "title.locked": 1,
                                "summary.value": season_synopsis,
                                "summary.locked": 1,
                            })
                            if self.replace_poster:
                                show.season(season_index).uploadArt(
                                    url=season_background)

                        episode_keys = season_data['collections'][season_id][0]['titleIds']

                        for episode_key in episode_keys:
                            episode = season_data['detail']['detail'][episode_key]
                            episode_index = episode['episodeNumber']
                            episode_title = episode['title']
                            episode_synopsis = episode['synopsis']
                            episode_poster = episode['images']['packshot']

                            print(
                                f"\n{season_title}第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_poster}")

                            if season_index and episode_index and not self.print_only:
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
        if 'atv_nb_lcl_zh_TW' not in self.url:
            self.url = re.sub(r'(.+ref=)(.+)',
                              '\\1atv_nb_lcl_zh_TW?language=zh_TW', self.url)
            self.logger.debug(self.url)
        res = self.session.get(self.url)
        if res.ok:
            match = re.findall(
                r'<script type=\"text/template\">(\{\"props\":\{\"state\".+)</script>', res.text)
            if match:
                data = orjson.loads(match[0])
                self.get_metadata(data['props']['state'])
