import sys
import re
import os
import logging
import json
from os.path import dirname
from http.cookiejar import MozillaCookieJar
import requests
from bs4 import BeautifulSoup
from services.service import Service
from common.utils import plex_find_lib, text_format
from common.dictionary import translate_text


class Netflix(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        id_search = re.search(r'\/(title|watch)\/(\d+)', self.url)
        self.netflix_id = id_search.group(2)

        dirPath = dirname(dirname(__file__)).replace("\\", "/")

        self.cookies = ""
        self.build = ""

        self.config = {
            "cookies_file": os.path.join(os.path.join(dirPath, 'config'), 'cookies.txt'),
            "cookies_txt": os.path.join(os.path.join(dirPath, 'config'), 'netflix.com_cookies.txt'),
            "language": "zh-Hant"
        }

        self.api = {
            'metadata_1': 'https://www.netflix.com/nq/website/memberapi/{build_id}/metadata?movieid={netflix_id}&imageFormat=webp&withSize=true&materialize=true&_=1641798218310',
            'metadata_2': 'https://www.netflix.com/api/shakti/{build_id}/metadata?movieid={netflix_id}&isWatchlistEnabled=false&isShortformEnabled=false&isVolatileBillboardsEnabled=false&drmSystem=widevine&languages={language}&imageFormat=webp'
        }

    def get_build(self, cookies):
        build_regex = r'"BUILD_IDENTIFIER":"([a-z0-9]+)"'

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

        res = session.get("https://www.netflix.com/browse", cookies=cookies)

        if not re.search(build_regex, res.text):
            print(
                "cannot get BUILD_IDENTIFIER from the cookies you saved from the browser..."
            )
            sys.exit()

        return re.search(build_regex, res.text).group(1)

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

    def shakti_api(self, url):
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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "X-Netflix.browserName": "Safari",
            "X-Netflix.browserVersion": "15",
            "X-Netflix.clientType": "akira",
            "X-Netflix.osFullName": "Mac OS X",
            "X-Netflix.osName": "Mac OS X",
            "X-Netflix.osVersion": "10.15.7"
        }

        resp = requests.get(
            url=url, headers=headers, cookies=self.cookies
        )

        if resp.ok:
            return resp.json()
        elif resp.status_code == 401:
            self.logger.warning("401 Unauthorized, cookies is invalid.")
        elif resp.text.strip() == "":
            self.logger.error(
                "title is not available in your Netflix region.")
            exit(-1)
        else:
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

            self.get_extra_poster(poster=show_poster,
                                  background=show_background)

            season_synopsis_list = []
            res = self.session.get(self.url)
            if res.ok:
                html_page = BeautifulSoup(res.text, 'lxml')

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

            episode_seq = 0
            for index, season in enumerate(data['seasons']):
                season_index = season['seq']
                season_title = season['title']
                season_synopsis = text_format(
                    season_synopsis_list[index])

                if index > 0:
                    episode_seq += len(data['seasons'][index-1]['episodes'])

                print(f"\n{season_title}\n{season_synopsis}")

                if not self.print_only:
                    if not self.season_index or self.season_index and self.season_index == season_index:
                        show.season(season_index).edit(**{
                            "title.value": season_title,
                            "title.locked": 1,
                            "summary.value": season_synopsis,
                            "summary.locked": 1,
                        })
                        if self.replace_poster and season_index == 1:
                            show.season(season_index).uploadPoster(
                                url=show_poster)

                for index, episode in enumerate(season['episodes'], start=1):
                    if episode['seq'] > episode_seq:
                        episode_index = episode['seq'] - episode_seq
                    elif index != episode['seq']:
                        episode_index = index
                    else:
                        episode_index = episode['seq']
                    episode_title = episode['title']

                    if not self.print_only and re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
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
        url = self.api['metadata_2'].format(
            build_id=self.build, netflix_id=self.netflix_id, language=self.config['language'])
        data = self.shakti_api(url)['video']

        extra_poster = next(
            img['url'] for img in data['boxart'] if img['w'] == 426)
        extra_background = next(
            img['url'] for img in data['storyart'] if img['w'] == 1920)

        if poster != extra_poster:
            print(f"\nExtra poster: {extra_poster}")
        if background != extra_background:
            print(f"\nExtra background: {extra_background}")

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
                        r'第 ([0-9]+) 季第 ([0-9]+) 集', episode_num)
                    if episode_regex:
                        season_index = int(episode_regex.group(1))
                        episode_index = int(episode_regex.group(2))
                        episode_title = (episode_text[0][2:]).strip()
                    else:
                        episode_regex = re.search(
                            r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
                        if episode_regex:
                            season_index = int(episode_regex.group(2))
                            episode_index = int(episode_regex.group(1))
                            episode_title = f'第 {episode_index} 集'
                else:
                    episode_num = episode_text[0].replace(
                        '播放“', '').replace('”', '')
                    episode_regex = re.search(
                        r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
                    if episode_regex:
                        season_index = int(episode_regex.group(2))
                        episode_index = int(episode_regex.group(1))
                    episode_title = (episode_num).strip()
                    if not re.search(r'[\u4E00-\u9FFF]', episode_title):
                        episode_title = f'第 {episode_index} 集'

                # if season_index == 1 and (episode_index == 9 or episode_index == 10):
                #     break

                if not self.print_only and re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
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
        if 'webcache' in self.url:
            res = self.session.get(self.url)
            if res.ok:
                html_page = BeautifulSoup(res.text, 'lxml')
                change_poster_only = False
                if not re.search(r'\/(sg-zh|hk|tw|mo)\/title', self.url):
                    change_poster_only = True
                if 'sg-zh' in self.url:
                    self.get_static_metadata(
                        html_page, change_poster_only, translate=True)
                else:
                    self.get_static_metadata(html_page, change_poster_only)
        else:
            self.cookies, self.build = self.read_userdata()
            url = self.api['metadata_1'].format(
                build_id=self.build, netflix_id=self.netflix_id)
            data = self.shakti_api(url)
            self.logger.debug("Metadata: %s", data)
            self.get_metadata(data['video'])
