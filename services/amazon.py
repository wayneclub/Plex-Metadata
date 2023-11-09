from __future__ import annotations
import re
from typing import Union
import orjson
from objects.titles import Title
from utils.collections import as_list
from services.baseservice import BaseService


class Amazon(BaseService):
    """
    Service code for the Amazon/Primevideo streaming service (https://www.primevideo.com/).

    \b
    Authorization: None
    """

    def __init__(self, args):
        super().__init__(args)
        self.pv = True if 'primevideo.com' in self.url else False

    def get_asin(self, title: str) -> str:
        """
        Get asin from url
        """
        asin = re.search(r'(detail|dp)\/([0-9a-zA-Z-.]+)', title)
        return asin.group(2) if asin else title

    def get_titles(self) -> Union[Title, list[Title]]:
        res = self.session.get(self.url)
        if res.ok:
            match = re.findall(
                r'<script type=\"text/template\">(\{\"props\":\{.*?\"state\".+)</script>', res.text)
            if match:
                data = orjson.loads(match[0])['props']['state']
            else:
                self.log.exit(
                    f" - Title ID '{self.url}' could not be found.")
        else:
            self.log.exit(res.text)

        title_id = data['pageTitleId']
        asins = set()
        if title_id in data['seasons']:
            for season in data['seasons'][title_id]:
                if self.pv:
                    asins.add(self.get_asin(season['seasonLink']))
                else:
                    asins.add(data['self'][season['seasonId']]['gti'])
        else:
            if self.pv:
                asins.add(self.get_asin(self.url))
            else:
                asins.add(data['self'][title_id]['gti'])

        return self.get_titles_prime(asins)

    def get_titles_prime(self, asins: set) -> list[Title]:
        """
        Get list of Titles for a primevideo.com (Prime) ASIN.
        """
        titles = []
        for asin in asins:
            res = self.session.get(
                url="https://www.primevideo.com/gp/video/api/getDetailPage",
                params={
                    "titleID": asin,
                    "isElcano": "1",
                    "sections": "Btf",
                    "language": "zh_TW",
                },
                headers={
                    "Accept": "application/json"
                },
                timeout=10
            )
            res.raise_for_status()
            data = res.json()
            data = data["widgets"]
            synopsis = ''
            season_synopsis = ''
            poster = ''
            if data["pageContext"]["subPageType"] == "Movie":
                self.movie = True
                cards = data["productDetails"]
                synopsis = cards['detail']['synopsis']
                poster = cards['detail']['images']['packshot']
            else:
                cards = data["titleContent"][0]["cards"]
                cards = list(filter(
                    lambda episode: episode['detail']['episodeNumber'] > 0, cards))
                season_synopsis = data["productDetails"]['detail']['synopsis']
                if data["productDetails"]['detail']['seasonNumber'] == 1:
                    synopsis = season_synopsis

            cards = [x["detail"]
                     for x in as_list(cards)]
            product_details = data["productDetails"]["detail"]

            for title in cards:
                titles.append(Title(
                    id_=asin,
                    type_=Title.Types.MOVIE if title["titleType"] == "movie" else Title.Types.TV,
                    name=product_details.get(
                        "parentTitle") or product_details["title"],
                    year=title.get(
                        "releaseYear") or product_details["releaseYear"],
                    synopsis=synopsis,
                    poster=poster,
                    season=product_details.get("seasonNumber"),
                    season_synopsis=season_synopsis,
                    episode=title.get("episodeNumber"),
                    episode_name=title.get("title"),
                    episode_synopsis=title.get("synopsis"),
                    episode_poster=title.get("images").get("covershot"),
                    source=self.source,
                    service_data=dict(**title, titleId=title["catalogId"])
                ))
        return titles
