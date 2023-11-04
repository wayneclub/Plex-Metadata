from __future__ import annotations
import re
import os
from typing import Union
from objects.titles import Title
from services.baseservice import BaseService


class KKTV(BaseService):
    """
    Service code for the KKTV streaming service (https://kktv.me/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.title = os.path.basename(self.url)

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        res = self.session.get(url=self.config["endpoints"]["titles"].format(
            title_id=self.title), timeout=10)
        if res.ok:
            data = res.json()['data']
            if data.get('title_type') == 'film':
                self.movie = True
        else:
            self.log.exit(res.text)

        title = data['title']
        title = title.replace('(日)', '').replace('(中)', '').strip()
        release_year = data['release_year']
        synopsis = data['summary']
        poster = data['cover'].replace('.xs', '.lg')

        if self.movie:
            titles.append(Title(
                id_=data['id'],
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                poster=poster,
                source=self.source,
                service_data=data['series'][0]['episodes'][0]
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)
            for season in data['series']:
                if len(data['series']) > 1:
                    season_index = int(re.findall(
                        r'第(.+)季', season['title'])[0].strip())

                for episode in season['episodes']:
                    episode_index = re.findall(
                        r'第(\d+)[集|話]', episode['title'])
                    if episode_index:
                        episode_index = int(episode_index[0])
                    else:
                        episode_index = int(
                            episode['id'].replace(episode['series_id'], ''))

                    titles.append(Title(
                        id_=episode['id'],
                        type_=Title.Types.TV,
                        name=title,
                        synopsis=synopsis,
                        poster=poster,
                        season=season_index,
                        episode=episode_index,
                        episode_name=episode['title'],
                        episode_poster=episode['still'].replace('.xs', '.lg'),
                        source=self.source,
                        service_data=episode
                    ))

        return titles
