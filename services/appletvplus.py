from __future__ import annotations
from datetime import datetime
from math import ceil
import os
from typing import Union
from objects.titles import Title
from services.baseservice import BaseService


class AppleTVPlus(BaseService):
    """
    Service code for the Apple TV+ streaming service (https://tv.apple.com/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.title = os.path.basename(self.url.split('?')[0])

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        if '/movie' in self.url:
            self.movie = True

        res = self.session.get(
            url=self.config['endpoints']['title'].format(
                content_type='movies' if self.movie else "shows", id=self.title),
            params=self.config["device"],
            timeout=10
        )
        if res.ok:
            data = res.json()['data']
            if not data.get('playables'):
                self.log.exit(
                    f" - Title ID '{self.title}' could not be found.")
        else:
            self.log.exit(f"Failed to load title manifest: {res.text}")

        title = data['content']['title']
        release_year = datetime.utcfromtimestamp(
            data['content']['releaseDate'] / 1000).year
        synopsis = data['content']['description']
        content_rating = data['content']['rating']['displayName']
        poster = data['content']['images']['posterArt']['url'].format(
            w=data['content']['images']['posterArt']['width'], h=data['content']['images']['posterArt']['height'], f='webp')
        if self.movie:
            playable_id = data['smartPlayables'][-1]['playableId']
            titles.append(Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=title,
                year=release_year,
                synopsis=synopsis,
                content_rating=content_rating,
                # poster=poster,
                source=self.source,
                service_data=data['playables'][playable_id]
            ))
        else:
            params = self.config['device'] | {
                'selectedSeasonEpisodesOnly': False}
            res = self.session.get(
                url=self.config['endpoints']['shows'].format(id=self.title),
                params=params,
                timeout=10
            )
            if res.ok:
                data = res.json()['data']
            else:
                self.log.exit(f"Failed to load episodes: {res.text}")

            episodes = filter(
                lambda episode: not episode.get('comingSoon'), self.get_episodes(total=data['totalEpisodeCount']))

            for episode in episodes:
                episode_data = self.get_episode(episode_id=episode['id'])
                playable_id = episode_data['smartPlayables'][-1]['playableId']
                titles.append(Title(
                    id_=self.title,
                    type_=Title.Types.TV,
                    name=episode["showTitle"],
                    synopsis=synopsis,
                    content_rating=content_rating,
                    # poster=poster,
                    season=episode["seasonNumber"],
                    episode=episode["episodeNumber"],
                    episode_name=episode.get("title"),
                    episode_synopsis=episode['description'],
                    episode_poster=episode['images']['posterArt']['url'].format(
                        w=episode['images']['posterArt']['width'], h=episode['images']['posterArt']['height'], f='webp'),
                    source=self.source,
                    service_data=episode_data['playables'][playable_id]
                ))
        return titles

    def get_episodes(self, total: int) -> list:
        """Get episodes"""
        pages = ceil(total / 10)
        next_tokens = [f'{(n)*10}:10' for n in range(pages)]

        episodes = []
        for next_token in next_tokens:
            params = self.config['device'] | {'nextToken': next_token}

            res = self.session.get(self.config['endpoints']['shows'].format(
                id=self.title), params=params, timeout=10)
            if res.ok:
                episodes += res.json()['data']['episodes']
            else:
                self.log.exit(res.text)
        return episodes

    def get_episode(self, episode_id: str) -> dict:
        """Get episode detail"""
        res = self.session.get(self.config['endpoints']['episode'].format(
            id=episode_id), params=self.config['device'], timeout=10)
        if res.ok:
            return res.json()['data']
        self.log.exit(res.text)
