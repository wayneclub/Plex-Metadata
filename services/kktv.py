import re
import os
import logging
import orjson
from utils.helper import plex_find_lib, text_format, save_html
from services.baseservice import BaseService


class KKTV(BaseService):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.api = {
            'play': 'https://www.kktv.me/play/{drama_id}010001'
        }

    def get_metadata(self, data):
        title = data['title'].strip()

        if not self.season_index:
            season_index = 1

        show_synopsis = text_format(data['summary'])
        show_poster = data['cover'].replace('.xs', '.lg')
        show_backgrounds = [img.replace('.xs', '.lg')
                            for img in data['stills']]

        print(f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_backgrounds}")

        if not self.print_only:
            show = plex_find_lib(self.plex, 'show', self.plex_title, title)

            if self.replace_poster:
                show.uploadPoster(url=show_poster)
                show.uploadArt(url=show_backgrounds[0])

        if 'series' in data:
            for season in data['series']:
                season_index = int(season['title'][1])
                if not self.print_only and season_index == 1:
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
                        show.season(season_index).uploadPoster(url=show_poster)

                for episode in season['episodes']:
                    episode_index = int(
                        episode['id'].replace(episode['seriesId'], ''))

                    episode_poster = episode['still'].replace('.xs', '.lg')

                    episode_title = episode['title']

                    if not self.print_only and re.search(r'第[0-9 ]+集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                        episode_title = show.season(
                            season_index).episode(episode_index).title
                    else:
                        episode_title = f'第 {episode_index} 集'

                    print(f"\n{episode_title}\n{episode_poster}")

                    if not self.print_only:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": episode_title,
                            "title.locked": 1,
                        })
                        if self.replace_poster:
                            show.season(season_index).episode(
                                episode_index).uploadPoster(url=episode_poster)

    def main(self):
        drama_id = os.path.basename(self.url)
        play_url = self.api['play'].format(drama_id=drama_id)

        res = self.session.get(play_url)
        if res.ok:
            match = re.search(r'({\"props\":{.*})', res.text)
            if match:
                data = orjson.loads(match.group(1))
                data = data['props']['initialState']['titles']['byId'][drama_id]
                self.get_metadata(data)
