import re
import logging
import orjson
from services.service import Service
from common.utils import plex_find_lib, save_html, text_format
from common.dictionary import convert_chinese_number


class IQIYI(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_metadata(self, data):
        title = data['videoAlbumInfo']['name']
        season_search = re.search(r'(.+)第(.+)季', title)
        if season_search:
            title = season_search.group(1).strip()
            season_index = int(convert_chinese_number(
                season_search.group(2)))
        else:
            season_index = self.season_index

        show_synopsis = text_format(data['videoAlbumInfo']['desc'])
        show_poster = re.sub(r'(.+)_\d+_\d+\.webp', 'https:\\1_2000_3000.webp',
                             data['videoAlbumInfo']['schemaAlbumImage'])
        self.logger.debug(data['videoAlbumInfo'])

        print(f"\n{title}\n{show_synopsis}\n{show_poster}")
        if not self.print_only:
            show = plex_find_lib(self.plex, 'show', self.plex_title, title)
            show.edit(**{
                "summary.value": show_synopsis,
                "summary.locked": 1,
            })

            if self.replace_poster:
                show.uploadPoster(url=show_poster)
                if season_index == 1:
                    show.season(season_index).uploadPoster(url=show_poster)

        episode_list = []
        if 'cacheAlbumList' in data and '1' in data['cacheAlbumList'] and len(data['cacheAlbumList']['1']) > 0:
            episode_list = data['cacheAlbumList']['1']
        elif 'play' in data and 'cachePlayList' in data['play'] and '1' in data['play']['cachePlayList'] and len(data['play']['cachePlayList']['1']) > 0:
            episode_list = data['play']['cachePlayList']['1']

        for episode in episode_list:
            if 'payMarkFont' in episode and episode['payMarkFont'] == 'Preview':
                break
            episode_regex = re.search(r'第(\d+)集', episode['name'])
            episode_index = int(episode_regex.group(1))
            episode_poster = re.sub(r'(.+)_\d+_\d+\.(webp|jpg)', 'https:\\1_1920_1080.webp',
                                    episode['imgUrl'])

            episode_title = f'第 {episode_index} 集'
            if not self.print_only and re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                episode_title = show.season(
                    season_index).episode(episode_index).title

            print(f"\n第 {season_index} 季第 {episode_index} 集\n{episode_poster}")

            if not self.print_only:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                })

                if self.replace_poster:
                    show.season(season_index).episode(
                        episode_index).uploadPoster(url=episode_poster)

    def main(self):
        res = self.session.get(self.url)
        if res.ok:
            match = re.search(r'({\"props\":{.*})', res.text)
            data = orjson.loads(match.group(1))
            self.get_metadata(data['props']['initialState']['album'])
