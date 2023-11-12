from __future__ import annotations
import re
from typing import Union
import orjson
from objects.titles import Title
from services.baseservice import BaseService


class Viu(BaseService):
    """
    Service code for the Viu streaming service (https://www.viu.com/).

    \b
    Authorization: None
    """
    # GEOFENCE = ["hk", "sig"]

    def __init__(self, args):
        super().__init__(args)
        self.area_id: str
        self.country_code: str
        self.language_flag_id: str

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        content_id = re.search(
            r'\/ott\/([^\/]+)\/([^\/]+)\/vod\/(\d+)', self.url)
        if content_id:
            country_code = content_id.group(1)
            language = content_id.group(2)
            content_id = content_id.group(3)
        else:
            self.log.exit(
                f" - Failed to get title: {self.url}")

        self.set_proxy(country_code)
        data = self.get_metadata(
            url=self.url, content_id=content_id, text='title', language=language)

        if data['current_product']['is_movie'] == 1:
            self.movie = True

        title = data['series']['name'].strip()
        title_aliases = data['current_product']['keyword'].split(',')[:3]
        synopsis = data['series']['description']
        poster = data['series']['cover_portrait_image_url']
        if self.movie:
            movie_info = self.get_title_info(
                title=title, title_aliases=title_aliases, is_movie=self.movie)
            if movie_info:
                release_year = movie_info['release_year']

            titles.append(Title(
                id_=data['current_product']['product_id'],
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                poster=poster,
                source=self.source
            ))
        else:
            title, season_index = self.get_title_and_season_index(title)

            series_info = self.get_title_info(
                title=title, title_aliases=title_aliases)
            if series_info:
                release_year = series_info['release_year']

            params = {
                'platform_flag_label': 'web',
                'area_id': self.area_id,
                'language_flag_id': self.language_flag_id,
                'platformFlagLabel': 'web',
                'areaId': self.area_id,
                'languageFlagId': self.language_flag_id,
                'countryCode': self.country_code,
                'r': '/vod/product-list',
                'os_flag_id': '1',
                'series_id': data['series']['series_id'],
                'size': '-1',
                'sort': 'asc',
            }

            res = self.session.get(
                self.config['endpoints']['titles'], params=params, timeout=10)
            if res.ok:
                episodes = res.json()['data']['product_list']
            else:
                self.log.exit(f" - Failed to get episodes: {res.text}")

            for episode in episodes:
                episode_index = int(episode['number'])
                episode_id = episode['product_id']

                titles.append(Title(
                    id_=episode_id,
                    type_=Title.Types.TV,
                    name=title,
                    synopsis=synopsis,
                    poster=poster,
                    season=season_index,
                    episode=episode_index,
                    episode_name=episode['synopsis'],
                    episode_synopsis=episode['description'],
                    episode_poster=episode['cover_landscape_image_url'],
                    source=self.source
                ))

        return titles

    def get_metadata(self, url: str, content_id: str, text: str, language: str = '') -> dict:
        """Get title metadata"""
        res = self.session.get(url=url, timeout=10)
        if res.ok:
            if 'no-service' in res.url:
                self.log.exit("Out of service!")
            match = re.search(
                r'<script id=\"__NEXT_DATA__" type=\"application/json\">(.+?)<\/script>', res.text)
            if match:
                data = orjson.loads(match.group(1).strip())[
                    'props']['pageProps']['initialProps']['fallback']
                product_detail = f'@"PRODUCT_DETAIL","{content_id}",0,true,'
                if product_detail in data:
                    area = data[product_detail]['server']['area']
                    self.area_id = area['area_id']
                    self.country_code = area['country']['code']
                    if language:
                        self.language_flag_id = next(
                            (lang['language_flag_id'] for lang in area['language'] if language in lang['mark']), '3')
                    return data[product_detail]['data']
                else:
                    self.log.exit("Wrong region, check your proxy!")
            else:
                self.log.exit(f" - Failed to get {text}: {res.text}")
        else:
            self.log.exit(f" - Failed to get {text}: {res.text}")
