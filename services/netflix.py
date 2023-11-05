from __future__ import annotations
from encodings import utf_8
import json
import sys
import re
import os
import logging
from time import time
from typing import Union
import orjson
import requests
from bs4 import BeautifulSoup
from constants import Service
from objects import Title
from services.baseservice import BaseService
from utils.cookies import Cookies
from utils.helper import download_file, driver_init, multi_thread_download, plex_find_lib, text_format
from utils.dictionary import translate_text
from utils.muxer import Muxer
from utils.subtitle import convert_subtitle


class Netflix(BaseService):
    """
    Service code for Netflix streaming service (https://www.netflix.com).

    \b
    Authorization: Cookies
    """

    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)
        self.title: str = ''
        # self.credential = self.config.credential(Service.NETFLIX)
        # self.cookies = Cookies(self.credential)

        # self.metadata_language = self.credential['metadata_language']

        # self.driver = ''
        # self.netflix_id = ''
        self.build_id: str = ''

        self.api = {
            'metadata_1': 'https://www.netflix.com/nq/website/memberapi/{build_id}/metadata?movieid={netflix_id}&imageFormat=webp&withSize=true&materialize=true&_=1641798218310',
            'metadata_2': 'https://www.netflix.com/api/shakti/{build_id}/metadata?movieid={netflix_id}&isWatchlistEnabled=false&isShortformEnabled=false&isVolatileBillboardsEnabled=false&drmSystem=widevine&languages={language}&imageFormat=webp',
            'trailer': 'https://www.netflix.com/playapi/cadmium/manifest/1?reqAttempt=1&reqName=manifest&clienttype=akira&uiversion=v9b6798ed&browsername=safari&browserversion=15.4.0&osname=mac&osversion=10.15.7'
        }

    def get_titles(self) -> Union[Title, list[Title]]:
        titles = []
        metadata = self.get_metadata()
        extra = self.get_extra()

        if metadata["type"] != "show":
            self.movie = True
        title = metadata['title']
        synopsis = metadata["synopsis"]
        poster = next(img['url']
                      for img in metadata['boxart'] if img['w'] == 426)
        background = next(
            img['url'] for img in metadata['storyart'] if img['w'] == 1920)
        self.get_extra_poster(poster=poster,
                              background=background)
        if self.movie:
            titles.append(Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=title,
                year=metadata["year"],
                synopsis=synopsis,
                poster=poster,
                background=background,
                source=self.source,
                service_data=metadata
            ))
        else:
            season_synopsis_list = []
            for season in extra.findAll('div', class_='season'):
                season_synopsis_list.append(season.find(
                    'p', class_='season-synopsis').get_text(strip=True))
            for index, season in enumerate(metadata['seasons']):
                for episode in season['episodes']:
                    titles.append(Title(
                        id_=self.title,
                        type_=Title.Types.TV,
                        name=title,
                        synopsis=synopsis,
                        poster=poster,
                        background=background,
                        season=season['seq'],
                        season_name=season['title'] if title != season['title'] else '',
                        season_synopsis=season_synopsis_list[index] if season_synopsis_list else '',
                        episode=episode['seq'],
                        episode_name=episode['title'],
                        episode_synopsis=episode['synopsis'],
                        episode_poster=next(
                            img['url'] for img in episode['stills'] if img['w'] == 1920),
                        source=self.source,
                        service_data=episode
                    ))
        return titles

    def get_build_id(self):
        """ Get BUILD_IDENTIFIER from cookies """

        headers = {
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.session.headers.get('User-Agent'),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "en,en-US;q=0.9",
        }

        res = self.session.get(
            url="https://www.netflix.com/browse", headers=headers, timeout=10)

        if res.ok:
            build_regex = re.search(
                r'"BUILD_IDENTIFIER":"([a-z0-9]+)"', res.text)
            if build_regex:
                return build_regex.group(1)
            else:
                self.log.exit(
                    " - Can't get BUILD_IDENTIFIER from the cookies you saved from the browser...")
        else:
            self.log.exit(res.text)

    def shakti_api(self, url: str):
        """ Get metadata from shakti api """

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "www.netflix.com",
            "Pragma": "no-cache",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": self.session.headers.get('User-Agent'),
            "X-Netflix.browserName": "Chrome",
            "X-Netflix.browserVersion": "98",
            "X-Netflix.clientType": "akira",
            "X-Netflix.osFullName": "Mac OS X",
            "X-Netflix.osName": "Mac OS X",
            "X-Netflix.osVersion": "10.15.7"
        }

        res = self.session.get(
            url=url, headers=headers, timeout=10
        )
        if res.ok:
            return res.json()
        elif res.status_code == 401:
            self.log.exit(
                " - Invalid cookies. (401 Unauthorized)")
            # os.remove(self.credential['cookies_file'])
        elif res.text.strip() == "":
            self.log.exit(
                " - Title is not available in your Netflix region.")
        else:
            # if os.path.exists(self.credential["cookies_file"]):
            #     os.remove(self.credential["cookies_file"])
            self.log.exit(
                " - Cookies expired!"
            )

    def get_metadata(self) -> dict:
        """
        Obtain Metadata information about a title by it's ID.
        :param title_id: Title's ID.
        :returns: Title Metadata.
        """
        if 'webcache' in self.url:
            print(self.url)
            # self.driver.get(self.url)
            # html_page = BeautifulSoup(self.driver.page_source, 'lxml')
            # change_poster_only = False
            # if not re.search(r'\/(sg-zh|hk|tw|mo)\/title', self.url):
            #     change_poster_only = True
            # if 'sg-zh' in self.url and self.metadata_language == 'zh-Hant':
            #     self.get_static_metadata(
            #         html_page, change_poster_only, translate=True)
            # else:
            #     self.get_static_metadata(html_page, change_poster_only)
        else:
            content_id = re.findall(
                r'(title\/|watch\/|browse.*\?.*jbv=|search.*\?.*jbv=)(\d+)', self.url.lower())
            if not content_id:
                self.log.exit("Netflix id not found: %s", self.url)

            self.title = content_id[0][-1]
            cookies = self.session.cookies.get_dict()
            if cookies.get('BUILD_IDENTIFIER'):
                self.build_id = cookies.get('BUILD_IDENTIFIER')
            else:
                self.build_id = self.get_build_id()
                # self.cookies.save_cookies(cookies, self.build_id)

            url = self.config['endpoints']['website'].format(
                build_id=self.build_id, id=self.title)

            return self.shakti_api(url)['video']

    def get_extra(self) -> dict:
        """ Get extra metadata """
        res = requests.get(self.config['endpoints']['title'].format(
            region=self.metadata['region'] or self.config['region'],
            id=self.title), timeout=10)
        if res.ok:
            return BeautifulSoup(res.text, 'html.parser')
        else:
            self.log.exit("Failed to load title: %s", res.text)

    def get_metadatas(self, data, html_page):
        title = data['title']

        if data['type'] == 'show':
            show_synopsis = text_format(data['synopsis'])
            show_background = next(
                img['url'] for img in data['storyart'] if img['w'] == 1920)
            show_poster = next(img['url']
                               for img in data['boxart'] if img['w'] == 426)

            print(f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_background}")

            self.get_extra_poster(poster=show_poster,
                                  background=show_background)

            season_synopsis_list = []

            for season in html_page.findAll('div', class_='season'):
                season_synopsis_list.append(season.find(
                    'p', class_='season-synopsis').get_text(strip=True))

            if not self.print_only:
                show = plex_find_lib(self.plex, 'show', self.plex_title, title)
                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })

                if self.replace_poster:
                    show.uploadPoster(url=show_poster)
                    show.uploadArt(url=show_background)

            for index, season in enumerate(data['seasons']):
                season_index = season['seq']
                season_title = season['title']

                if season_synopsis_list:
                    season_synopsis = text_format(
                        season_synopsis_list[index])

                print(f"\n{season_title}\n{season_synopsis}")

                if not self.print_only:
                    if not self.season_index or self.season_index and self.season_index == season_index:
                        show.season(season_index).edit(**{
                            "title.value": season_title,
                            "title.locked": 1,
                            "summary.value": season_synopsis,
                            "summary.locked": 1,
                        })
                        if self.replace_poster and season_index == 1 and len(data['seasons']) == 1:
                            show.season(season_index).uploadPoster(
                                url=show_poster)

                for episode in season['episodes']:
                    episode_index = episode['seq']
                    episode_title = episode['title']

                    if not self.print_only and re.search(r'第 \d+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                        episode_title = show.season(
                            season_index).episode(episode_index).title

                    episode_synopsis = text_format(episode['synopsis'])

                    if not self.print_only and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).summary):
                        episode_synopsis = show.season(
                            season_index).episode(episode_index).summary

                    episode_poster = next(
                        img['url'] for img in episode['stills'] if img['w'] == 1920)

                    print(
                        f"\n第 {season_index} 季第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_poster}")

                    if not self.print_only:
                        if not self.season_index or self.season_index and self.season_index == season_index:
                            show.season(season_index).episode(episode_index).edit(**{
                                "title.value": episode_title,
                                "title.locked": 1,
                                "summary.value": episode_synopsis,
                                "summary.locked": 1,
                            })

                            if self.replace_poster:
                                show.season(season_index).episode(
                                    episode_index).uploadPoster(url=episode_poster)
        elif data['type'] == 'movie':
            movie_synopsis = text_format(data['synopsis'])
            movie_background = next(
                img['url'] for img in data['storyart'] if img['w'] == 1920)
            movie_poster = next(
                img['url'] for img in data['boxart'] if img['w'] == 426)

            print(
                f"\n{title}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

            self.get_extra_poster(
                poster=movie_poster, background=movie_background)

            if not self.print_only:
                show = plex_find_lib(self.plex, 'movie',
                                     self.plex_title, title)
                show.edit(**{
                    "summary.value": movie_synopsis,
                    "summary.locked": 1,
                })

                if self.replace_poster:
                    show.uploadPoster(url=movie_poster)
                    show.uploadArt(url=movie_background)

    def get_extra_poster(self, poster, background):
        """ Get extra poster and background """

        url = self.config['endpoints']['shakti'].format(
            build_id=self.build_id, id=self.title, language='en_us')
        data = self.shakti_api(url)['video']

        extra_poster = next(
            img['url'] for img in data['boxart'] if img['w'] == 426)
        extra_background = next(
            img['url'] for img in data['storyart'] if img['w'] == 1920)

        if poster != extra_poster:
            print(f"\nExtra poster: {extra_poster}")
        if background != extra_background:
            print(f"\nExtra background: {extra_background}")

    def get_trailer(self, trailer, title):
        trailer_id = trailer['id']
        trailer_title = trailer['title']

        cookies = self.cookies.get_cookies()

        payload = {
            "version": 2,
            "url": "manifest",
            "id": int(time() * 100000000),
            "languages": [
                "zh-TW"
            ],
            "params": {
                "type": "standard",
                "manifestVersion": "v2",
                "viewableId": trailer_id,
                "profiles": [
                    "heaac-2-dash",
                    "heaac-2hq-dash",
                    "playready-h264mpl30-dash",
                    "playready-h264mpl31-dash",
                    "playready-h264mpl40-dash",
                    "playready-h264hpl30-dash",
                    "playready-h264hpl31-dash",
                    "playready-h264hpl40-dash",
                    "dfxp-ls-sdh",
                    "simplesdh",
                    "nflx-cmisc",
                    "imsc1.1",
                    "BIF240",
                    "BIF320"
                ],
                "flavor": "SUPPLEMENTAL",
                "drmType": "fairplay",
                "drmVersion": 25,
                "usePsshBox": True,
                "isBranching": False,
                "useHttpsStreams": True,
                "supportsUnequalizedDownloadables": True,
                "imageSubtitleHeight": 720,
                "uiVersion": "shakti-v9b6798ed",
                "uiPlatform": "SHAKTI",
                "clientVersion": "6.0034.747.911",
                "supportsPreReleasePin": True,
                "supportsWatermark": True,
                "titleSpecificData": {
                    f"{trailer_id}": {
                        "unletterboxed": True
                    }
                },
                "preferAssistiveAudio": False,
                "isUIAutoPlay": True,
                "isNonMember": False,
                "desiredVmaf": "plus_lts",
                "desiredSegmentVmaf": "plus_lts",
                "requestSegmentVmaf": False,
                "supportsPartialHydration": False,
                "contentPlaygraph": [
                    "start"
                ],
                "showAllSubDubTracks": False,
                "maxSupportedLanguages": 2
            }
        }

        res = self.session.post(self.api['trailer'],
                                cookies=cookies, data=orjson.dumps(payload))

        if res.ok:
            print(res.json())
            data = res.json()['result']
            folder_path = os.path.join(os.path.join(
                self.download_path, title), 'Trailers')
            video_tracks = data['video_tracks'][0]
            max_height = str(video_tracks.get('maxHeight'))
            max_width = str(video_tracks.get('maxWidth'))
            video_track = video_tracks['streams'][-1]
            audio_track = data['audio_tracks'][0]['streams'][-1]
            audio_language = audio_track['language']
            audio_language = self.config.get_language_code(audio_language)
            audio_language = next(
                (language[0] for language in self.config.language_list() if audio_language in language), audio_language)

            input_video = os.path.join(
                folder_path, f"{trailer_title} [{max_height}p].mp4")
            input_audio = os.path.join(
                folder_path, f"{trailer_title} {audio_language}.aac")

            os.makedirs(folder_path, exist_ok=True)

            subtitles = list()

            for subtitle in data['timedtexttracks']:
                if subtitle.get('language') and not subtitle.get('isForcedNarrative'):
                    subtitle_language = self.config.get_language_code(
                        subtitle['language'])
                    subtitle_file = os.path.join(
                        folder_path, f"{trailer_title} {subtitle_language}.dfxp")
                    sub_key = list(subtitle['ttDownloadables']['imsc1.1']['downloadUrls'].keys(
                    ))[0]
                    subtitle_url = subtitle['ttDownloadables']['imsc1.1']['downloadUrls'][sub_key]
                    subtitles.append(
                        {'name': subtitle_file, 'url': subtitle_url})

            multi_thread_download(subtitles)

            download_file(url=video_track['urls']
                          [0]['url'], output_path=input_video)
            download_file(url=audio_track['urls']
                          [0]['url'], output_path=input_audio)

            convert_subtitle(folder_path=folder_path)

            mkvmuxer = Muxer(
                title=trailer_title,
                folder_path=folder_path,
                max_height=max_height,
                max_width=max_width,
                source=Platform.NETFLIX
            )
            muxed_file = mkvmuxer.start_mux()

            output = muxed_file.replace(
                os.path.basename(muxed_file), f"{trailer['title']}.mkv")

            os.rename(muxed_file, output)

            self.logger.info("\n%s ...Done!",
                             os.path.basename(output))

        else:
            print(res.text)

    def get_static_metadata(self, html_page, change_poster_only=False, translate=False):
        title = html_page.find(
            'h1', class_='title-title').get_text(strip=True)

        show_synopsis = text_format(html_page.find(
            'div', class_='title-info-synopsis').get_text(strip=True))

        show_background = html_page.find(
            'picture', class_='hero-image-loader').find_all('source')[-1]['srcset']

        if translate:
            title = translate_text(title)
            show_synopsis = translate_text(show_synopsis)

        print(f"\n{title}\n{show_synopsis}\n{show_background}")

        if not self.print_only:
            show = plex_find_lib(self.plex, 'show', self.plex_title, title)

            if not change_poster_only:
                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })
            if self.replace_poster:
                show.uploadArt(url=show_background)

        for season in html_page.find_all('div', class_='season'):

            season_synopsis = text_format(season.find(
                'p', class_='season-synopsis').get_text(strip=True))
            if translate:
                season_synopsis = translate_text(season_synopsis)

            print(f"\n{season_synopsis}\n")

            episode_list = season.find_all('div', class_='episode')

            for episode in episode_list:

                episode_text = episode.find(
                    'img', class_='episode-thumbnail-image')['alt']
                episode_text = episode_text.replace('。。', '。').split('。')

                if len(episode_text) > 1:
                    episode_num = episode_text[1]

                    episode_regex = re.search(
                        r'第 (\d+) 季第 (\d+) 集', episode_num)
                    if episode_regex:
                        season_index = int(episode_regex.group(1))
                        episode_index = int(episode_regex.group(2))
                        episode_title = (episode_text[0][2:]).strip()
                    else:
                        episode_regex = re.search(
                            r'Watch (.+?)\. Episode (\d+) of Season (\d+)\.', episode_num)
                        if episode_regex:
                            season_index = int(episode_regex.group(2))
                            episode_index = int(episode_regex.group(3))
                            episode_title = episode_regex.group(1).strip()
                        else:
                            episode_regex = re.search(
                                r'Episode (\d+) of Season (\d+)\.', episode_num)
                            if episode_regex:
                                season_index = int(episode_regex.group(2))
                                episode_index = int(episode_regex.group(1))
                                episode_title = f'第 {episode_index} 集'
                else:
                    episode_num = episode_text[0].replace(
                        '播放“', '').replace('”', '')
                    episode_regex = re.search(
                        r'Watch (.+?)\. Episode (\d+) of Season (\d+)\.', episode_num)
                    if episode_regex:
                        season_index = int(episode_regex.group(2))
                        episode_index = int(episode_regex.group(3))
                        episode_title = episode_regex.group(1).strip()
                    else:
                        episode_regex = re.search(
                            r'Episode (\d+) of Season (\d+)\.', episode_num)
                        if episode_regex:
                            season_index = int(episode_regex.group(2))
                            episode_index = int(episode_regex.group(1))
                        episode_title = (episode_num).strip()
                        if not re.search(r'[\u4E00-\u9FFF]', episode_title):
                            episode_title = f'第 {episode_index} 集'

                # if season_index == 1 and (episode_index == 9 or episode_index == 10):
                #     break

                if not self.print_only and re.search(r'第 \d+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                    episode_title = show.season(
                        season_index).episode(episode_index).title

                episode_synopsis = text_format(
                    episode.find('p').get_text(strip=True))

                episode_img = episode.find(
                    'img', class_='episode-thumbnail-image')['src']

                if translate:
                    episode_title = translate_text(episode_title)
                    episode_synopsis = translate_text(episode_synopsis)

                print(f"\n{episode_title}\n{episode_synopsis}\n{episode_img}")

                # season_index = 2

                if not self.print_only and season_index and episode_index == 1 and not change_poster_only:
                    show.season(season_index).edit(**{
                        "title.value": f'第 {season_index} 季',
                        "title.locked": 1,
                        "summary.value": season_synopsis,
                        "summary.locked": 1,
                    })

                # if season_index == 2:
                    # episode_index = episode_index - show.season(1).leafCount
                # elif season_index == 3:
                #     episode_index = episode_index - \
                #         (show.season(1).leafCount + show.season(2).leafCount)
                # elif season_index == 4:
                #     season_index = 3
                #     episode_index = episode_index - \
                #         (show.season(1).leafCount + show.season(2).leafCount)
                # elif season_index == 5:
                #     season_index = 4
                #     episode_index = episode_index - \
                #         (show.season(1).leafCount +
                #          show.season(2).leafCount + show.season(3).leafCount)

                if not self.print_only and season_index and episode_index:
                    if 2 * len(episode_list) == show.season(season_index).leafCount:
                        if self.replace_poster:
                            show.season(season_index).episode(
                                2*episode_index-1).uploadPoster(url=episode_img)
                            show.season(season_index).episode(
                                2*episode_index).uploadPoster(url=episode_img)
                        if re.search(r'第 \d+ 集', episode_title):
                            episode_title_1 = f'第 {2*episode_index-1} 集'
                            episode_title_2 = f'第 {2*episode_index} 集'
                        else:
                            episode_title_1 = episode_title
                            episode_title_2 = episode_title

                        if not change_poster_only:
                            show.season(season_index).episode(2*episode_index-1).edit(**{
                                "title.value": episode_title_1,
                                "title.locked": 1,
                                "summary.value": episode_synopsis,
                                "summary.locked": 1,
                            })
                            show.season(season_index).episode(2*episode_index).edit(**{
                                "title.value": episode_title_2,
                                "title.locked": 1,
                                "summary.value": episode_synopsis,
                                "summary.locked": 1,
                            })
                    else:
                        if not change_poster_only:
                            show.season(season_index).episode(episode_index).edit(**{
                                "title.value": episode_title,
                                "title.locked": 1,
                                "summary.value": episode_synopsis,
                                "summary.locked": 1,
                            })

                        if self.replace_poster:
                            show.season(season_index).episode(
                                episode_index).uploadPoster(url=episode_img)

    def main(self):
        self.driver = driver_init()
        if 'webcache' in self.url:
            self.driver.get(self.url)
            html_page = BeautifulSoup(self.driver.page_source, 'lxml')
            change_poster_only = False
            if not re.search(r'\/(sg-zh|hk|tw|mo)\/title', self.url):
                change_poster_only = True
            if 'sg-zh' in self.url and self.metadata_language == 'zh-Hant':
                self.get_static_metadata(
                    html_page, change_poster_only, translate=True)
            else:
                self.get_static_metadata(html_page, change_poster_only)
        else:
            netflix_id = re.findall(
                r'(title\/|watch\/|browse.*\?.*jbv=|search.*\?.*jbv=)(\d+)', self.url.lower())
            if not netflix_id:
                self.logger.error("\nCan't detect netflix id: %s", self.url)
                sys.exit(-1)
            self.netflix_id = netflix_id[0][-1]
            self.logger.debug("netflix_id: %s", netflix_id)

            self.cookies.load_cookies('NetflixId')
            cookies = self.cookies.get_cookies()
            if cookies.get('BUILD_IDENTIFIER'):
                self.build_id = cookies.get('BUILD_IDENTIFIER')
            else:
                self.build_id = self.get_build_id(cookies)
                self.cookies.save_cookies(cookies, self.build_id)

            url = self.api['metadata_1'].format(
                build_id=self.build_id, netflix_id=self.netflix_id)

            data = self.shakti_api(url)
            self.logger.debug("Metadata: %s", data)

            self.driver.get(self.url)
            html_page = BeautifulSoup(self.driver.page_source, 'lxml')
            # print(data)
            self.get_metadatas(data['video'], html_page)

        if 'additionalVideos' in self.driver.page_source:
            self.logger.info("\nDownload trailer:")
            trailer_regex = re.search(
                r'(\{"type":"additionalVideos","data":.+\}\}),\{"type":"seasonsAndEpisodes"', self.driver.page_source)
            content = ""
            if trailer_regex:
                content = trailer_regex.group(1)
            else:
                trailer_regex = re.search(
                    r'(\{"type":"additionalVideos","data":.+\}\}),\{"type":"moreDetails"', self.driver.page_source)
                if trailer_regex:
                    content = trailer_regex.group(1)
            if content:
                trailer_data = orjson.loads(content.encode().decode(
                    'unicode-escape'))['data']
                # print(trailer_data)
                # for trailer in trailer_data['supplementalVideos']:
                #     self.get_trailer(
                #         trailer=trailer, title=trailer_data['subheaderText'])

        self.driver.quit()
