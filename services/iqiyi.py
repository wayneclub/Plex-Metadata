from __future__ import annotations
import re
from typing import Union
import orjson
from objects.titles import Title
from services.baseservice import BaseService


class IQIYI(BaseService):
    """
    Service code for the iQIYI streaming service (https://www.iq.com/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        if 'play/' in self.url:
            content_id = re.search(
                r'https://www.iq.com/play/.+\-([^-]+)\?lang=.+', self.url)
            if not content_id:
                content_id = re.search(
                    r'https://www.iq.com/play/([^-]+)', self.url)
            self.url = f'https://www.iq.com/album/{content_id.group(1)}'

        res = self.session.get(url=self.url, timeout=10)
        if res.ok:
            match = re.search(r'({\"props\":{.*})', res.text)
            if not match:
                self.log.exit(f" - Failed to get title: {self.url}")

            data = orjson.loads(match.group(1))['props']
            mode_code = data['initialProps']['pageProps']['modeCode']
            lang_code = data['initialProps']['pageProps']['langCode']
            data = data['initialState']['album']['videoAlbumInfo']
            if data['videoType'] == 'singleVideo':
                self.movie = True
        else:
            self.log.exit(res.text)

        title = data['name'].strip()
        release_year = data['year']
        synopsis = data['desc'].strip()
        poster = re.sub(r'(.+)_\d+_\d+\.webp',
                        'https:\\1_2200_3000.webp', data['schemaAlbumImage'])
        if self.movie:
            titles.append(Title(
                id_=data['qipuId'],
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                poster=poster,
                source=self.source
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)
            for episode in self.get_episodes(pages=data['totalPageRange'], album_id=data['albumId'], mode_code=mode_code, lang_code=lang_code):
                if 'payMarkFont' in episode and episode['payMarkFont'] == 'Preview':
                    break
                if 'order' in episode:
                    episode_index = int(episode['order'])
                    titles.append(Title(
                        id_=episode['qipuId'],
                        type_=Title.Types.TV,
                        name=title,
                        synopsis=synopsis,
                        poster=poster,
                        season=season_index,
                        episode=episode_index,
                        episode_poster=re.sub(r'(.+)\.(webp|jpg)', '\\1_1920_1080.webp',
                                              episode['albumWebpPic']).replace('http:', 'https:'),
                        source=self.source
                    ))
        return titles

    def get_episodes(self, pages: list, album_id: str, mode_code: str, lang_code: str) -> list:
        """Get episodes"""
        episodes = []
        for page in pages:
            episodes_url = self.config['endpoints']['episodes'].format(
                album_id=album_id, mode_code=mode_code, lang_code=lang_code, device_id=self.session.cookies.get_dict().get('QC005'), end_order=page['to'], start_order=page['from'])
            res = self.session.get(url=episodes_url, timeout=10)
            if res.ok:
                data = res.json()
                episodes += data['data']['epg']
            else:
                self.log.error(res.text)
        return episodes
