from __future__ import annotations
import re
import logging
from typing import Union
import orjson
from bs4 import BeautifulSoup
from objects import Title
from services.baseservice import BaseService


class HamiVideo(BaseService):
    """
    Service code for the Friday streaming service (https://hamivideo.hinet.net/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        res = self.session.get(self.url, timeout=10)
        if res.ok:
            web_content = BeautifulSoup(res.text, 'html.parser')
            match = web_content.findAll(
                'script', attrs={'type': 'application/ld+json'})
            if match:
                data = orjson.loads(
                    str(match[0].string).strip().replace(',]', ']'))

                title_content = web_content.find('div', class_='title')
                if title_content.find('h3'):
                    data['english_title'] = title_content.find(
                        'h3').getText(strip=True)

                data['release_year'] = title_content.find(
                    'p').getText(strip=True).split('．')[0]

                language = web_content.find(
                    'ul', class_='list_detail').find('h3', text='發音').find_next('span').text
                if not language:
                    language = web_content.find('span', class_=re.compile(
                        r'language\d+')).get('data')
                data['original_lang'] = language

                series = web_content.find('ul', class_='program_class_in')
                if series:
                    episodes = []
                    for episode in series.findAll('li'):
                        episode_index = episode.find('p').getText(strip=True)
                        if episode_index.isdigit():
                            episode_index = int(
                                episode.find('p').getText(strip=True))
                            if episode_index != 0:
                                episodes.append({
                                    'index': episode_index,
                                    'episode_id': episode['data-id'],
                                    'free': 1 if episode.find('div', class_='t_free') else 0
                                })

                else:
                    vod_regex = re.search(
                        r"sendUrl\(.*?,'(OTT_VOD_.*?)','(.*?)','.*?'\);", res.text)
                    if vod_regex:
                        content_id = vod_regex.group(1)
                        free = int(vod_regex.group(2))
                        self.movie = True
                    else:
                        self.log.exit(f" - Failed to get title: {self.url}")

        else:
            self.log.exit(res.text)

        title = data['name']
        if 'release_year' in data:
            release_year = data['release_year']
        else:
            release_year = data['datePublished'][:4]

        content_rating = data['contentRating']
        synopsis = data['description'].replace(
            'Hami Video', '').split('線上看，')[-1].split(' 導演:')[0].strip()
        poster = data['image']

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
                    'episode_id': content_id,
                    'free': free
                }
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)
            for episode in episodes:
                titles.append(Title(
                    id_=self.url,
                    type_=Title.Types.TV,
                    name=title,
                    content_rating=content_rating,
                    poster=poster,
                    season=season_index,
                    episode=episode['index'],
                    episode_name="",
                    source=self.source,
                    service_data=episode
                ))

        return titles
