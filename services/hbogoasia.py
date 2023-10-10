import re
import os
import logging
from urllib.parse import urlparse
from utils.helper import plex_find_lib, get_static_html, text_format
from services.baseservice import BaseService


class HBOGOAsia(BaseService):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.territory = ""

        self.api = {
            'geo': 'https://api2.hbogoasia.com/v1/geog?lang=zh-Hant&version=0&bundleId={bundle_id}',
            'tvseason': 'https://api2.hbogoasia.com/v1/tvseason/list?parentId={parent_id}&territory={territory}',
            'tvepisode': 'https://api2.hbogoasia.com/v1/tvepisode/list?parentId={parent_id}&territory={territory}',
            'movie': 'https://api2.hbogoasia.com/v1/movie?contentId={content_id}&territory={territory}',
        }

    def get_territory(self):
        geo_url = self.api['geo'].format(bundle_id=urlparse(self.url).netloc)
        response = self.session.get(geo_url)
        if response.ok:
            if 'territory' in response.json():
                self.territory = response.json()['territory']
                self.logger.debug(self.territory)
            else:
                self.logger.info("\nOut of service!")
                exit(0)

    def get_metadata(self):
        if '/sr' in self.url:
            series_id_regex = re.search(
                r'https:\/\/www\.hbogoasia.+\/sr(\d+)', self.url)
            if series_id_regex:
                series_id = series_id_regex.group(1)
                series_url = self.api['tvseason'].format(
                    parent_id=series_id, territory=self.territory)
            else:
                self.logger.error("\nSeries not found!")
                exit(1)

            res = self.session.get(series_url)
            if res.ok:
                season_list = res.json()['results']
                self.logger.debug(season_list)
                if len(season_list) > 0:
                    if season_list[0]['metadata']['titleInformations'][-1]['lang'] != 'ENG':
                        title = season_list[0]['metadata']['titleInformations'][-1]['name']
                        show_synopsis = season_list[0]['metadata']['titleInformations'][-1]['summary']
                    else:
                        title = season_list[0]['metadata']['titleInformations'][0]['name']
                        show_synopsis = season_list[0]['metadata']['titleInformations'][0]['summary']
                    title = re.sub(r'\(第\d+季\)', '', title).strip()
                    show_synopsis = text_format(show_synopsis)
                else:
                    self.logger.info(
                        "\nThe series isn't available in this region.")

                title = re.sub(r'S\d+', '', title).strip()

                show_poster = season_list[0]['imagePortrait']
                show_background = season_list[0]['image']

                print(
                    f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_background}")

                if not self.print_only:
                    show = plex_find_lib(
                        self.plex, 'show', self.plex_title, title)
                    show.edit(**{
                        "summary.value": show_synopsis,
                        "summary.locked": 1,
                    })

                    if self.replace_poster:
                        show.uploadPoster(url=show_poster)
                        show.uploadArt(url=show_background)

                for season in season_list:
                    season_index = season['seasonNumber']
                    season_title = f'第 {season_index} 季'

                    season_url = self.api['tvepisode'].format(
                        parent_id=season['contentId'], territory=self.territory)
                    self.logger.debug(season_url)

                    season_background = ""
                    for image in season['materials']:
                        if 'largescreen_thumbnail' in image['href']:
                            season_background = image['href']
                        if 'portrait' in image['href']:
                            show_poster = image['href']
                    season_synopsis = text_format(next((title_info['summary'] for title_info in season['metadata']['titleInformations']
                                                        if title_info['lang'] == 'CHN')))
                    if not re.search(r'[\u4E00-\u9FFF]', season_synopsis):
                        season_synopsis = text_format(
                            show.season(season_index).summary)

                    self.logger.info("\n%s\n%s\n%s", season_title,
                                     season_synopsis, season_background)

                    if season_index and not self.print_only:
                        if season_index == 1 and re.search(r'[\u4E00-\u9FFF]', season_synopsis):
                            show.edit(**{
                                "summary.value": season_synopsis,
                                "summary.locked": 1,
                            })
                        show.season(season_index).edit(**{
                            "title.value": season_title,
                            "title.locked": 1,
                            "summary.value": season_synopsis,
                            "summary.locked": 1,
                        })
                        if self.replace_poster:
                            if len(season_list) == 1:
                                show.uploadArt(url=season_background)
                            show.season(season_index).uploadArt(
                                url=season_background)

                    episode_res = self.session.get(season_url)
                    if episode_res.ok:
                        episode_list = episode_res.json()['results']
                        self.logger.debug(episode_list)
                        for episode in episode_list:

                            episode_index = episode['episodeNumber']

                            episode_title = f'第 {episode_index} 集'

                            episode_synopsis = text_format(next((title_info['description'] for title_info in episode['metadata']['titleInformations']
                                                                 if title_info['lang'] == 'CHN')))

                            episode_poster = episode['image']

                            if not self.print_only and re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                                episode_title = text_format(show.season(
                                    season_index).episode(episode_index).title)

                            print(
                                f"\n{episode_title}\n{episode_synopsis}\n{episode_poster}")

                            if season_index and episode_index and not self.print_only:
                                show.season(season_index).episode(episode_index).edit(**{
                                    "title.value": episode_title,
                                    "title.locked": 1,
                                    "summary.value": episode_synopsis,
                                    "summary.locked": 1,
                                })
                                if self.replace_poster:
                                    show.season(season_index).episode(
                                        episode_index).uploadPoster(url=episode_poster)

        else:
            content_id = os.path.basename(self.url)
            movie_url = self.api['movie'].format(
                content_id=content_id, territory=self.territory)

            res = self.session.get(movie_url)
            if res.ok:
                data = res.json()
                title_info = next(
                    title for title in data['metadata']['titleInformations'] if title['lang'] == 'CHN')
                title = title_info['name']
                # content_rating = f"tw/{data['rating']['displayName']}"
                movie_synopsis = text_format(title_info['description'])
                movie_poster = data['imagePortrait']
                movie_background = data['image']
                print(
                    f"\n{title}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

                if not self.print_only:
                    movie = plex_find_lib(self.plex, 'movie',
                                          self.plex_title, title)
                    movie.edit(**{
                        # "contentRating.value": content_rating,
                        # "contentRating.locked": 1,
                        "summary.value": movie_synopsis,
                        "summary.locked": 1,
                    })
                    if self.replace_poster:
                        movie.uploadPoster(url=movie_poster)
                        movie.uploadArt(url=movie_background)

    def main(self):
        self.get_territory()
        self.get_metadata()


# def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False):
#     title = driver.find_element(
#         By.XPATH, "//div[@class='series-title']").text.strip()

#     print(f"\n{title}")

#     if not print_only:
#         show = plex_find_lib(plex, 'show', plex_title, title)

#     parent_id_regex = re.search(
#         r'https:\/\/www.hbogoasia.tw\/series\/sr(\d+)', driver.current_url)
#     parent_id = parent_id_regex.group(1)
#     parent_url = f'https://api2.hbogoasia.com/v1/tvseason/list?parentId={parent_id}&territory=TWN'

#     driver.quit()
#     season_list = get_static_html(parent_url, True)['results']
#     for season in season_list:
#         season_index = season['seasonNumber']
#         season_url = f"https://api2.hbogoasia.com/v1/tvepisode/list?parentId={season['contentId']}&territory=TWN"
#         season_title = f'第 {season_index} 季'

#         for image in season['materials']:
#             if 'largescreen_thumbnail' in image['href']:
#                 season_background = image['href']
#             if 'portrait' in image['href']:
#                 show_poster = image['href']
#         season_synopsis = text_format(next((title_info['summary'] for title_info in season['metadata']['titleInformations']
#                                             if title_info['lang'] == 'CHN')))
#         if not re.search(r'[\u4E00-\u9FFF]', season_synopsis):
#             season_synopsis = text_format(show.season(season_index).summary)

#         print(f"\n{season_title}\n{season_synopsis}\n{season_background}")

#         if season_index and not print_only:
#             if season_index == 1 and re.search(r'[\u4E00-\u9FFF]', season_synopsis):
#                 show.edit(**{
#                     "summary.value": season_synopsis,
#                     "summary.locked": 1,
#                 })
#             show.season(season_index).edit(**{
#                 "title.value": season_title,
#                 "title.locked": 1,
#                 "summary.value": season_synopsis,
#                 "summary.locked": 1,
#             })
#             if replace_poster:
#                 if len(season_list) == 1:
#                     show.uploadArt(url=season_background)
#                 show.season(season_index).uploadArt(url=season_background)

#         for episode in get_static_html(season_url, True)['results']:
#             episode_index = episode['episodeNumber']

#             episode_title = f'第 {episode_index} 集'

#             episode_synopsis = text_format(next((title_info['description'] for title_info in episode['metadata']['titleInformations']
#                                                  if title_info['lang'] == 'CHN')))

#             episode_poster = episode['image']

#             if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
#                 episode_title = text_format(show.season(
#                     season_index).episode(episode_index).title)

#             print(
#                 f"\n{episode_title}\n{episode_synopsis}\n{episode_poster}")

#             if season_index and episode_index and not print_only:
#                 show.season(season_index).episode(episode_index).edit(**{
#                     "title.value": episode_title,
#                     "title.locked": 1,
#                     "summary.value": episode_synopsis,
#                     "summary.locked": 1,
#                 })
#                 if replace_poster:
#                     show.season(season_index).episode(
#                         episode_index).uploadPoster(url=episode_poster)
