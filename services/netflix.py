import sys
import re
import os
import logging
import json
from os.path import dirname
from http.cookiejar import MozillaCookieJar
import requests
from services.service import Service
from common.utils import plex_find_lib, text_format, get_static_html


class Netflix(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        id_search = re.search(r'\/title\/(\d+)', self.url)
        self.netflix_id = id_search.group(1)

        dirPath = dirname(dirname(__file__)).replace("\\", "/")

        self.cookies = ""
        self.build = ""

        self.config = {
            "cookies_file": os.path.join(os.path.join(dirPath, 'config'), 'cookies.txt'),
            "cookies_txt": os.path.join(os.path.join(dirPath, 'config'), 'netflix.com_cookies.txt'),
            "metada_language": "zh-Hant"
        }

    def get_build(self, cookies):
        BUILD_REGEX = r'"BUILD_IDENTIFIER":"([a-z0-9]+)"'

        session = requests.Session()
        session.headers = {
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "en,en-US;q=0.9",
        }

        r = session.get("https://www.netflix.com/browse", cookies=cookies)

        if not re.search(BUILD_REGEX, r.text):
            print(
                "cannot get BUILD_IDENTIFIER from the cookies you saved from the browser..."
            )
            sys.exit()

        return re.search(BUILD_REGEX, r.text).group(1)

    def save(self, cookies, build):
        cookie_data = {}
        for name, value in cookies.items():
            cookie_data[name] = [value, 0]
        logindata = {"BUILD_IDENTIFIER": build, "cookies": cookie_data}
        with open(self.config["cookies_file"], "w", encoding="utf8") as f:
            f.write(json.dumps(logindata, indent=4))
            f.close()
        os.remove(self.config["cookies_txt"])

    def read_userdata(self):
        cookies = None
        build = None

        if not os.path.isfile(self.config["cookies_file"]):
            try:
                cj = MozillaCookieJar(self.config["cookies_txt"])
                cj.load()
            except Exception:
                print("invalid netscape format cookies file")
                sys.exit()

            cookies = dict()

            for cookie in cj:
                cookies[cookie.name] = cookie.value

            build = self.get_build(cookies)
            self.save(cookies, build)

        with open(self.config["cookies_file"], "rb") as f:
            content = f.read().decode("utf-8")

        if "NetflixId" not in content:
            self.logger.warning("(Some) cookies expired, renew...")
            return cookies, build

        jso = json.loads(content)
        build = jso["BUILD_IDENTIFIER"]
        cookies = jso["cookies"]
        for cookie in cookies:
            cookie_data = cookies[cookie]
            value = cookie_data[0]
            if cookie != "flwssn":
                cookies[cookie] = value
        if cookies.get("flwssn"):
            del cookies["flwssn"]

        return cookies, build

    def shakti_api(self, nfid):
        url = f"https://www.netflix.com/api/shakti/{self.build}/metadata"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "es,ca;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "www.netflix.com",
            "Pragma": "no-cache",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
            "X-Netflix.browserName": "Chrome",
            "X-Netflix.browserVersion": "79",
            "X-Netflix.clientType": "akira",
            "X-Netflix.esnPrefix": "NFCDCH-02-",
            "X-Netflix.osFullName": "Windows 10",
            "X-Netflix.osName": "Windows",
            "X-Netflix.osVersion": "10.0",
            "X-Netflix.playerThroughput": "1706",
            "X-Netflix.uiVersion": self.build,
        }

        params = {
            "movieid": nfid,
            "drmSystem": "widevine",
            "isWatchlistEnabled": "false",
            "isShortformEnabled": "false",
            "isVolatileBillboardsEnabled": "false",
            "languages": self.config["metada_language"],
        }

        while True:
            resp = requests.get(
                url=url, headers=headers, params=params, cookies=self.cookies
            )

            if resp.status_code == 401:
                self.logger.warning("401 Unauthorized, cookies is invalid.")
            elif resp.text.strip() == "":
                self.logger.error(
                    "title is not available in your Netflix region.")
                exit(-1)

            try:
                return resp.json()

            except Exception:
                # os.remove(self.config["cookies_file"])
                self.logger.warning(
                    "Error getting metadata: Cookies expired\nplease fetch new cookies.txt"
                )
                exit(-1)

    def get_metadata(self, data):
        title = data['title']

        if data['type'] == 'show':
            show_synopsis = text_format(data['synopsis'])
            show_background = next(
                img['url'] for img in data['storyart'] if img['w'] == 1920)
            show_poster = next(img['url']
                               for img in data['boxart'] if img['w'] == 426)

            print(f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_background}")

            html_page = get_static_html(self.url)
            season_synopsis_list = []
            for season in html_page.find_all('div', class_='season'):
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

            for season in data['seasons']:
                season_regex = re.search(r'S(\d+)', season['shortName'])
                season_index = int(season_regex.group(1))
                season_title = season['title']
                season_synopsis = text_format(
                    season_synopsis_list[season['seq']-1])

                print(f"\n{season_title}\n{season_synopsis}")

                if not self.print_only:
                    show.season(season_index).edit(**{
                        "title.value": season_title,
                        "title.locked": 1,
                        "summary.value": season_synopsis,
                        "summary.locked": 1,
                    })
                    if self.replace_poster and len(data['seasons']) == 1:
                        show.season(season_index).uploadPoster(url=show_poster)

                for episode in season['episodes']:
                    episode_index = episode['seq']
                    episode_title = episode['title']

                    if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                        episode_title = show.season(
                            season_index).episode(episode_index).title

                    episode_synopsis = text_format(episode['synopsis'])
                    episode_poster = next(
                        img['url'] for img in episode['stills'] if img['w'] == 1920)

                    print(
                        f"\n第 {season_index} 季 {episode_title}\n{episode_synopsis}\n{episode_poster}")

                    if not self.print_only:
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

    def main(self):
        self.cookies, self.build = self.read_userdata()
        data = self.shakti_api(self.netflix_id)
        # print("Metadata: {}".format(data))
        self.get_metadata(data['video'])


# def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False, season_index=1, change_poster_only=False, translate=False):
#     title = html_page.find(
#         'h1', class_='title-title').get_text(strip=True)
#     if translate:
#         title = translate_text(title)
#     print(f"\n{title}")

#     if not print_only:
#         show = plex_find_lib(plex, 'show', plex_title, title)

#     show_synopsis = text_format(html_page.find(
#         'div', class_='title-info-synopsis').get_text(strip=True))
#     if translate:
#         show_synopsis = translate_text(show_synopsis)

#     show_background = html_page.find(
#         'picture', class_='hero-image-loader').find_all('source')[-1]['srcset']

#     if show and not print_only and not change_poster_only and season_index == 1:
#         show.edit(**{
#             "summary.value": show_synopsis,
#             "summary.locked": 1,
#         })
#         if replace_poster:
#             show.uploadArt(url=show_background)

#     for season in html_page.find_all('div', class_='season'):

#         season_synopsis = text_format(season.find(
#             'p', class_='season-synopsis').get_text(strip=True))
#         if translate:
#             season_synopsis = translate_text(season_synopsis)
#         print(f"\n{season_synopsis}\n")

#         episode_list = season.find_all('div', class_='episode')

#         multi_episode = False

#         for episode in episode_list:

#             episode_text = episode.find(
#                 'img', class_='episode-thumbnail-image')['alt']
#             episode_text = episode_text.replace('。。', '。').split('。')

#             if len(episode_text) > 1:
#                 episode_num = episode_text[1]

#                 episode_regex = re.search(
#                     r'第 ([0-9]+) 季第 ([0-9]+) 集', episode_num)
#                 if episode_regex:
#                     season_index = int(episode_regex.group(1))
#                     episode_index = int(episode_regex.group(2))
#                     episode_title = (episode_text[0][2:]).strip()
#                 else:
#                     episode_regex = re.search(
#                         r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
#                     if episode_regex:
#                         season_index = int(episode_regex.group(2))
#                         episode_index = int(episode_regex.group(1))
#                         episode_title = f'第 {episode_index} 集'
#             else:
#                 episode_num = episode_text[0].replace(
#                     '播放“', '').replace('”', '')
#                 episode_regex = re.search(
#                     r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
#                 if episode_regex:
#                     season_index = int(episode_regex.group(2))
#                     episode_index = int(episode_regex.group(1))
#                 episode_title = (episode_num).strip()
#                 if not re.search(r'[\u4E00-\u9FFF]', episode_title):
#                     episode_title = f'第 {episode_index} 集'

#             print(episode_num)

#             # if season_index == 1 and (episode_index == 9 or episode_index == 10):
#             #     break

#             if 2 * len(episode_list) == show.season(season_index).leafCount:
#                 multi_episode = True

#             if translate:
#                 episode_title = translate_text(episode_title)

#             if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
#                 episode_title = show.season(
#                     season_index).episode(episode_index).title

#             if episode_title:
#                 print(f"{episode_title}\n")

#             episode_synopsis = text_format(
#                 episode.find('p').get_text(strip=True))

#             if translate:
#                 episode_synopsis = translate_text(episode_synopsis)

#             print(f"{episode_synopsis}\n")

#             episode_img = episode.find(
#                 'img', class_='episode-thumbnail-image')['src']

#             print(f"{episode_img}\n")
#             # season_index = 2

#             if season_index and episode_index == 1 and not change_poster_only and not print_only:
#                 show.season(season_index).edit(**{
#                     "title.value": f'第 {season_index} 季',
#                     "title.locked": 1,
#                     "summary.value": season_synopsis,
#                     "summary.locked": 1,
#                 })

#             # if season_index == 2:
#                 # episode_index = episode_index - show.season(1).leafCount
#             # elif season_index == 3:
#             #     episode_index = episode_index - \
#             #         (show.season(1).leafCount + show.season(2).leafCount)
#             # elif season_index == 4:
#             #     season_index = 3
#             #     episode_index = episode_index - \
#             #         (show.season(1).leafCount + show.season(2).leafCount)
#             # elif season_index == 5:
#             #     season_index = 4
#             #     episode_index = episode_index - \
#             #         (show.season(1).leafCount +
#             #          show.season(2).leafCount + show.season(3).leafCount)

#             if season_index and episode_index and not print_only:
#                 if multi_episode:
#                     if replace_poster:
#                         show.season(season_index).episode(
#                             2*episode_index-1).uploadPoster(url=episode_img)
#                         show.season(season_index).episode(
#                             2*episode_index).uploadPoster(url=episode_img)
#                     if re.search(r'第 \d+ 集', episode_title):
#                         episode_title_1 = f'第 {2*episode_index-1} 集'
#                         episode_title_2 = f'第 {2*episode_index} 集'
#                     else:
#                         episode_title_1 = episode_title
#                         episode_title_2 = episode_title

#                     if not change_poster_only:
#                         show.season(season_index).episode(2*episode_index-1).edit(**{
#                             "title.value": episode_title_1,
#                             "title.locked": 1,
#                             "summary.value": episode_synopsis,
#                             "summary.locked": 1,
#                         })
#                         show.season(season_index).episode(2*episode_index).edit(**{
#                             "title.value": episode_title_2,
#                             "title.locked": 1,
#                             "summary.value": episode_synopsis,
#                             "summary.locked": 1,
#                         })
#                 else:
#                     if replace_poster:
#                         show.season(season_index).episode(
#                             episode_index).uploadPoster(url=episode_img)

#                     if not change_poster_only:
#                         show.season(season_index).episode(episode_index).edit(**{
#                             "title.value": episode_title,
#                             "title.locked": 1,
#                             "summary.value": episode_synopsis,
#                             "summary.locked": 1,
#                         })
