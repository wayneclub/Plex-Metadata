from __future__ import annotations
import os
import re
from typing import Union
from cn2an import cn2an
from bs4 import BeautifulSoup
import orjson
from objects.titles import Title
from services.baseservice import BaseService


class MyVideo(BaseService):
    """
    Service code for the MyVideo streaming service (https://www.myvideo.net.tw/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        res = self.session.get(url=self.url, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, 'html.parser')
        else:
            self.log.exit(res.text)

        data = dict()
        release_year = ''
        for meta in soup.find_all('li', class_='introList'):
            if meta.text.isdigit() and len(meta.text) == 4:
                release_year = meta.text
                break

        data = orjson.loads(soup.find_all(
            'script', type='application/ld+json')[2].text)
        if not data:
            self.log.exit(f" - Failed to get title: {self.url}")

        if data.get('@type') == 'Movie':
            self.movie = True

        title = data['name'].replace('預告', '').replace(' 搶先版', '').strip()
        content_rating = re.search(r'"rating": \'(.+)\'', res.text)
        if content_rating:
            content_rating = content_rating.group(1)
        synopsis = data['description'].replace(f'《{title}》', '')
        poster = data['image']
        if self.movie:
            movie_id = os.path.basename(self.url)
            titles.append(Title(
                id_=movie_id,
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                content_rating=content_rating,
                poster=poster,
                source=self.source,
                service_data=movie_id
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)
            season_list = []
            for season in soup.find('ul', class_='seasonSelectorList').find_all('a'):
                season_search = re.search(r'第(.+?)季', season.text)
                if season_search and not '國語版' in season.text:
                    season_list.append({
                        'index': int(cn2an(season_search.group(1))),
                        'url': f"https://www.myvideo.net.tw/{season['href']}",
                    })
            if not season_list:
                season_list.append({
                    'index': season_index,
                    'url': self.url,
                })

            for season in season_list:
                for episode in self.get_episodes(season_url=season['url']):
                    titles.append(Title(
                        id_=episode['id'],
                        type_=Title.Types.TV,
                        name=title,
                        synopsis=synopsis,
                        content_rating=content_rating,
                        poster=poster,
                        season=season['index'],
                        episode=episode['index'],
                        episode_name=episode['name'],
                        episode_synopsis=episode['synopsis'],
                        episode_poster=episode['poster'],
                        source=self.source,
                        service_data=episode['id']
                    ))

        return titles

    def get_episodes(self, season_url: str) -> list:
        """Get episodes"""
        episodes = []
        res = self.session.get(season_url, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, 'html.parser')
            for episode in soup.find_all('span', class_='episodeIntro'):
                poster = episode.find_previous_sibling(
                    'span').find('img')['src']
                title = episode.find('a')
                episode_search = re.search(r'第(\d+)集', title.text)
                if episode_search and not '預告' in title.text:
                    episodes.append({
                        'index': int(episode_search.group(1)),
                        'id': os.path.basename(title['href']),
                        'name': title.text.split('【')[-1].replace('】', '').strip(),
                        'synopsis': episode.find('blockquote').text,
                        'poster': poster
                    })
        else:
            self.log.exit(" - Failed to get episodes")

        return episodes
