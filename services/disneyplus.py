from __future__ import annotations
import os
from math import ceil
from typing import Union
from objects import Title
from services.baseservice import BaseService


class DisneyPlus(BaseService):
    """
    Service code for Disney+ streaming service (https://disneyplus.com).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.title = os.path.basename(self.url)

    def get_titles(self) -> Union[Title, list[Title]]:
        if '/movies' in self.url:
            self.movie = True

        title_type = "Video" if self.movie else "Series"
        res = self.session.get(self.config['endpoints']['titles'].format(
            content_type=f'Dmc{title_type}Bundle',
            region=self.metadata['region'] or self.config['region'],
            language=self.default_language or self.config['language'],
            encoded_type='encodedFamilyId' if self.movie else 'encodedSeriesId',
            content_id=self.title
        ), timeout=10)
        if res.ok:
            data = res.json()['data'][f"Dmc{title_type}Bundle"]
        else:
            self.log.exit(f"Failed to load title: {res.text}")

        if data[title_type.lower()] is None:
            self.log.exit(
                "Disney+ returned no information on this title.\n"
                "It might not be available in the account's region."
            )

        if self.movie:
            title = data['video']['text']['title']['full']['program']['default']['content']
            release_year = data['video']['releases'][0]['releaseYear']
            synopsis = data['video']['text']['description']['medium']['program']['default']['content']
            poster = data['video']['image']['tile']['0.71']['program']['default']['url']
            if 'background_details' in data['video']['image']:
                background = data['video']['image']['background_details']['1.78']['program']['default']['url']
            elif 'background' in data['video']['image']:
                background = data['video']['image']['background']['1.78']['program']['default']['url']

            extras = set()
            extras.add(data['video']['image']['tile']
                       ['1.78']['program']['default']['url'])
            if 'background_up_next' in data['video']['image']:
                extras.add(data['video']['image']['background_up_next']
                           ['1.78']['program']['default']['url'])
            if 'tile_inline' in data['video']['image']:
                extras.add(data['video']['image']['tile_inline']
                           ['0.71']['program']['default']['url'])
            if 'thumbnail' in data['video']['image']:
                extras.add(data['video']['image']['thumbnail']
                           ['1.78']['program']['default']['url'])

            return Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                poster=poster,
                background=background,
                source=self.source,
                service_data=data["video"],
                extra=extras
            )
        else:
            title = data['series']['text']['title']['full']['series']['default']['content']
            release_year = data['series']['releases'][0]['releaseYear']
            synopsis = data['series']['text']['description']['medium']['series']['default']['content']
            if 'background_details' in data['series']['image']:
                background = data['series']['image']['background_details']['1.78']['series']['default']['url']
            elif 'background' in data['series']['image']:
                background = data['series']['image']['background']['1.78']['series']['default']['url']

            extras = set()
            extras.add(data['series']['image']['tile']
                       ['1.78']['series']['default']['url'])
            if 'background_up_next' in data['series']['image']:
                extras.add(data['series']['image']['background_up_next']
                           ['1.78']['series']['default']['url'])
            if 'tile_inline' in data['series']['image']:
                extras.add(data['series']['image']['tile_inline']
                           ['0.71']['series']['default']['url'])
            if 'thumbnail' in data['series']['image']:
                extras.add(data['series']['image']['thumbnail']
                           ['1.78']['program']['default']['url'])

        # get data for every episode in every season via looping due to the fact
        # that the api doesn't provide ALL episodes in the initial bundle api call.
        seasons: dict[str, list] = {s["seasonId"]: []
                                    for s in data["seasons"]["seasons"]}
        for season in data["seasons"]["seasons"]:
            season_id = season["seasonId"]
            page_size = ceil(season["episodes_meta"]["hits"] / 30)
            for page_number in range(1, page_size+1):
                seasons[season_id].extend(self.get_episodes(
                    season_id=season_id, page_number=page_number))

        episodes = [x for y in seasons.values() for x in y]

        return [Title(
            id_=self.title,
            type_=Title.Types.TV,
            name=title,
            synopsis=synopsis,
            poster=episode['image']['tile']['0.71']['series']['default']['url'],
            background=background,
            season=episode['seasonSequenceNumber'],
            season_synopsis=episode['text']['description']['medium']['season']['default']['content'] if episode['text']['description']['medium'].get(
                'season') else '',
            episode=episode['episodeSequenceNumber'],
            episode_name=episode['text']['title']['full']['program']['default']['content'],
            episode_synopsis=episode['text']['description']['full']['program']['default']['content'],
            episode_poster=episode['image']['thumbnail']['1.78']['program']['default']['url'],
            compress=True,
            source=self.source,
            service_data=episode,
            extra=extras
        ) for episode in episodes]

    def get_episodes(self, season_id: str, page_number: int) -> list:
        """Get episodes"""
        res = self.session.get(self.config['endpoints']['episodes'].format(
            region=self.metadata['region'] or self.config['region'],
            language=self.default_language or self.config['language'],
            season_id=season_id,
            page_number=page_number
        ), timeout=10)
        if res.ok:
            return res.json()['data']['DmcEpisodes']['videos']
        else:
            self.log.exit(" - Failed to get episodes")
