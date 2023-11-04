from __future__ import annotations
from datetime import datetime
from typing import Union
from urllib.parse import parse_qs, urlparse

import requests
from objects.titles import Title
from services.baseservice import BaseService


class GooglePlay(BaseService):
    """
    Service code for the Google Play streaming service (https://play.google.com/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.title = parse_qs(urlparse(self.url).query).get('id')[0]

    def get_titles(self) -> Union[Title, list[Title]]:
        if '/movies' in self.url:
            self.movie = True

        res = requests.get(
            url=self.config["endpoints"]["titles"],
            params={
                "id": f"yt:{'movie' if self.movie else 'show'}:{self.title}",
                "if": "mibercg:ANN:HDP:PRIM",
                'alt': 'json',
                'devtype': '4',
                'device': 'generic',
                'make': 'Google',
                'model': 'ChromeCDM-Mac-x86-64',
                'product': 'generic',
                'apptype': '2',
                "cr": "TW",  # US
                "lr": "zh-TW",  # en-US
            },
            headers=self.session.headers,
            cookies=self.session.cookies.get_dict(),
            timeout=10
        )
        if res.ok:
            data = res.json()
            if not 'resource' in data:
                self.log.exit(f" - Failed to get titles {self.title}")
            data = data["resource"]
        else:
            error = res.json()['error']
            self.log.exit("%s (%s)", error['message'], error['status'])

        if self.movie:
            return [Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=x['metadata']['title'].split('  ')[0],
                year=datetime.utcfromtimestamp(
                    int(x['metadata']['release_date_timestamp_sec'])).year,
                synopsis=x['metadata']['description'],
                poster=next(
                    image['url'] for image in x['metadata']['images'] if image['type'] == 'TYPE_POSTER') + '=w2000',
                source=self.source,
                service_data=x
            ) for x in data if x["resource_id"]["type"] == "MOVIE"]

        title = [x["metadata"]["title"]
                 for x in data if x["resource_id"]["type"] == "SHOW"][0]
        seasons = {
            # seasons without an mid are "Complete Series", just filter out
            x["resource_id"]["id"]: x["metadata"]["sequence_number"]
            for x in data if x["resource_id"]["type"] == "SEASON" and x["resource_id"].get("mid")
        }

        return [Title(
            id_=self.title,
            type_=Title.Types.TV,
            name=title,
            season=seasons[t["parent"]["id"]],
            episode=t["metadata"]["sequence_number"],
            episode_name=t["metadata"].get("title"),
            source=self.source,
            service_data=t
        ) for t in data if t["resource_id"]["type"] == "EPISODE" and t["parent"]["id"] in seasons]
