
from __future__ import annotations
import re
from time import time
from typing import Union
from requests.exceptions import RequestException
from objects import Title
from services.baseservice import BaseService


class FridayVideo(BaseService):
    """
    Service code for the Friday streaming service (https://video.friday.tw/).

    \b
    Authorization: Cookies
    """

    def __init__(self, args):
        super().__init__(args)

        self.monitor_url: str
        cookies = self.session.cookies.get_dict()
        cookies['JSESSIONID'] = ''
        cookies['login_accessToken'] = ''
        self.session.cookies.update(cookies)

    def get_content_type(self, content_type) -> int:
        """Get content type"""
        program = {
            'movie': 1,
            'drama': 2,
            'anime': 3,
            'show': 4
        }

        if program.get(content_type):
            return program.get(content_type)

    def get_content_rating(self, rating: str) -> str:
        """Get content rating"""
        content_rating = {
            '1': '普遍級',
            '2': '保護級',
            '5': '輔12級',
            '3': '輔15級',
            '4': '限制級'
        }

        if content_rating.get(rating):
            return content_rating.get(rating)

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        content_search = re.search(
            r'(https:\/\/video\.friday\.tw\/(drama|anime|movie|show)\/detail\/(\d+))', self.url)
        if content_search:
            self.monitor_url = content_search.group(1)
            content_id = content_search.group(3)
            content_type = self.get_content_type(content_search.group(2))
            if content_type == 1:
                self.movie = True
        else:
            self.log.exit(
                f" - Failed to get title: {self.url}")

        try:
            res = self.session.post(self.config["endpoints"]["titles"].format(
                content_id=content_id, content_type=content_type), timeout=10)
        except RequestException as error:
            if '/pkmslogout' in str(error):
                self.log.exit(" - Cookies expired, please renew cookies!")
            else:
                self.log.exit(error)

        self.fet_monitor(self.monitor_url)
        if res.ok:
            if '/pkmslogout' in res.text:
                self.log.exit(
                    "Cookies is expired! Please re-download cookies!")
            else:
                data = res.json()
                if data.get('data'):
                    data = data['data']['content']
                else:
                    self.log.exit(data['message'])
        else:
            self.log.exit(res.text)

        title = data['chineseName'].strip()
        original_title = data['englishName'].replace('，', ',')
        release_year = data['year']
        synopsis = data['introduction']
        content_rating = self.get_content_rating(str(data['rating']))
        poster = f"https://vbmspic.video.friday.tw{data['imageUrl']}".replace(
            '.jpg', '_XL.jpg')
        if self.movie:
            titles.append(Title(
                id_=self.url,
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                content_rating=content_rating,
                poster=poster,
                source=self.source,
                service_data={
                    'streaming_id': data['streamingId'],
                    'streaming_type': data['streamingType'],
                    'content_type':  data['contentType'],
                    'content_id':  data['contentId'],
                    'subtitle': False
                }
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)
            episodes = self.get_episodes(
                content_id=data['contentId'], content_type=data['contentType'])
            for episode in self.filter_episodes(episodes, season_index):
                titles.append(Title(
                    id_=self.url,
                    type_=Title.Types.TV,
                    name=title,
                    content_rating=content_rating,
                    poster=poster,
                    season=episode['season_index'],
                    episode=episode['episode_index'],
                    episode_name=episode['separationName'],
                    episode_synopsis=episode['separationIntroduction'],
                    episode_poster=f"https://vbmspic.video.friday.tw{episode['stillImageUrl']}".replace(
                        '.jpg', '_XL.jpg'),
                    autocrop=True,
                    source=self.source,
                    service_data={
                        'streaming_id': episode['streamingId'],
                        'streaming_type': episode['streamingType'],
                        'content_type':  episode['contentType'],
                        'content_id':  episode['contentId'],
                        'subtitle':  'false'
                    }
                ))

        return titles

    def get_episodes(self, content_id: str, content_type: str) -> list:
        """Get episodes"""
        res = self.session.get(self.config["endpoints"]["episodes"].format(
            content_id=content_id, content_type=content_type), timeout=10)
        if res.ok:
            data = res.json()
            if data.get('data'):
                return data['data']
            else:
                self.log.exit(" - Failed to get series data")
        else:
            self.log.exit(res.text)

    def filter_episodes(self, data: dict, season_index: int) -> list:
        """
        Filter episodes
        """
        episodes = []
        for episode in data['episodeList']:
            episode_index = re.search(
                r'^(sp)*(\d+)$', episode['episodeName'].lower())
            if episode_index:
                episode['episode_index'] = int(episode_index.group(2))
                episode['season_index'] = 0 if episode_index.group(
                    1) else season_index
                episodes.append(episode)
        return episodes

    def fet_monitor(self, url) -> None:
        """Check api call from friday website"""

        data = f'${int(time())*1000}'

        res = self.session.post(
            url=self.config['endpoints']['fet_monitor'].format(url=url), data=data, timeout=10)
        if res.ok:
            if res.text == 'OK(Webserver)':
                return True
            else:
                self.log.exit(res.text)
        else:
            self.log.exit(res.text)
