import re
import time
import os
from bs4 import BeautifulSoup
import orjson

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import logging
from common.utils import plex_find_lib, save_html, text_format
from services.service import Service


class AppleTV(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.api = {
            'episodes': 'https://tv.apple.com/api/uts/v2/view/show/{show_id}/episodes?utscf=OjAAAAAAAAA~&utsk=6e3013c6d6fae3c2%3A%3A%3A%3A%3A%3A235656c069bb0efb&caller=web&sf=143470&v=54&pfm=web&locale=zh-Hant&skip=0&count=100'
        }

    def get_metadata(self, data):
        title = data['title']

        if data['type'] == 'Movie':
            content_rating = f"tw/{data['rating']['displayName']}"
            movie_synopsis = text_format(data['description'])
            movie_poster = data['images']['coverArt']['url'].format(
                w=data['images']['coverArt']['width'], h=data['images']['coverArt']['height'], f='webp')
            movie_background = data['images']['centeredFullScreenBackgroundImage']['url'].format(
                w=4320, h=2160, c='sr', f='webp')
            print(
                f"\n{title}\n{content_rating}\n{movie_synopsis}\n{movie_poster}\n{movie_background}")

            if not self.print_only:
                movie = plex_find_lib(self.plex, 'movie',
                                      self.plex_title, title)
                movie.edit(**{
                    "contentRating.value": content_rating,
                    "contentRating.locked": 1,
                    "summary.value": movie_synopsis,
                    "summary.locked": 1,
                })
                if self.replace_poster:
                    movie.uploadPoster(url=movie_poster)
                    movie.uploadArt(url=movie_background)
        elif data['type'] == 'Show':
            show_synopsis = text_format(data['description'])
            show_poster = data['images']['coverArt']['url'].format(
                w=data['images']['coverArt']['width'], h=data['images']['coverArt']['height'], f='webp')
            show_background = data['images']['centeredFullScreenBackgroundImage']['url'].format(
                w=4320, h=2160, c='sr', f='webp')
            print(
                f"\n{title}\n{show_synopsis}\n{show_poster}\n{show_background}")

            if not self.print_only:
                show = plex_find_lib(self.plex, 'show',
                                     self.plex_title, title)
                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1,
                })
                if self.replace_poster:
                    show.uploadPoster(url=show_poster)
                    show.uploadArt(url=show_background)

            res = self.session.get(self.api['episodes'].format(
                show_id=os.path.basename(self.url)))
            if res.ok:
                for episode in res.json()['data']['episodes']:
                    season_index = episode['seasonNumber']
                    episode_index = episode['episodeNumber']
                    episode_title = episode['title']
                    episode_synopsis = text_format(episode['description'])
                    episode_poster = episode['images']['previewFrame']['url'].format(
                        w=episode['images']['previewFrame']['width'], h=episode['images']['previewFrame']['height'], f='webp')

                    print(
                        f"\n第 {season_index} 季 第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_poster}")

                    if not self.print_only:
                        if episode_index == 1:
                            if season_index == 1:
                                show.season(season_index).edit(**{
                                    "title.value": f'第 {season_index} 季',
                                    "title.locked": 1,
                                    "summary.value": show_synopsis,
                                    "summary.locked": 1,
                                })
                                if self.replace_poster:
                                    show.season(season_index).episode(
                                        episode_index).uploadPoster(url=show_poster)
                            else:
                                show.season(season_index).edit(**{
                                    "title.value": f'第 {season_index} 季',
                                    "title.locked": 1,
                                })
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": episode_title,
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
                        if self.replace_poster:
                            show.season(season_index).episode(
                                episode_index).uploadPoster(url=episode_poster)

    def main(self):
        res = self.session.get(self.url)
        if res.ok:
            html_page = BeautifulSoup(res.text, 'lxml')
            data = orjson.loads(html_page.find(
                'script', id='shoebox-uts-api').string.strip())
            key = next(key for key in list(data.keys())
                       if f'{os.path.basename(self.url)}.caller.web' in key)

            self.get_metadata(orjson.loads(data[key])['d']['data']['content'])


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False, season_index=1):
    time.sleep(3)

    title = WebDriverWait(driver, 20).until(EC.visibility_of_element_located(
        (By.XPATH, "//p[contains(@class, 'preview-product-header__title')]"))).text
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    show_synopsis = text_format(WebDriverWait(driver, 20).until(EC.visibility_of_element_located(
        (By.XPATH, "//div[contains(@class, 'product-header__content__details__synopsis')]"))).text)
    print(f"\n{show_synopsis}\n")

    if not print_only and season_index == 1:
        show.edit(**{
            "summary.value": show_synopsis,
            "summary.locked": 1,
        })

        show.season(season_index).edit(**{
            "title.value": f'第 {season_index} 季',
            "title.locked": 1,
            "summary.value": show_synopsis,
            "summary.locked": 1,
        })

    print(f"\n第 {season_index} 季")

    previous_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.XPATH, "//button[@aria-label='Previous Page']")))
    while not previous_button.get_property('disabled'):
        ActionChains(driver).move_to_element(
            previous_button).click(previous_button).perform()
        time.sleep(1)
        previous_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.XPATH, "//button[@aria-label='Previous Page']")))

    time.sleep(1)

    next_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.XPATH, "//button[@aria-label='Next Page']")))

    while not next_button.get_property('disabled'):
        ActionChains(driver).move_to_element(
            next_button).click(next_button).perform()
        time.sleep(1)
        next_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.XPATH, "//button[@aria-label='Next Page']")))

    time.sleep(2)
    html_page = BeautifulSoup(driver.page_source, 'lxml')
    for episode in html_page.find_all('div', attrs={'data-lockups-show-page-episode': True}):
        print(episode)
        episode_number = episode.find(
            'div', class_='episode-lockup__content__episode-number').get_text(strip=True)

        episode_regex = re.search(
            r'第 (\d+) 集', episode_number)
        if episode_regex:
            episode_index = int(episode_regex.group(1))
            if episode_index == 1 and episode['data-episode-index'] != '0':
                season_index += 1
                print(f"\n第 {season_index} 季")

        episode_title = episode.find(
            'div', class_='episode-lockup__content__title').get_text(strip=True)
        episode_synopsis = text_format(episode.find(
            'p', class_='episode-lockup__description').get_text(strip=True))

        print(f"\n{episode_number}：{episode_title}\n{episode_synopsis}")

        posters = episode.find(
            'source', attrs={'type': 'image/webp'})['srcset'].split(', ')
        poster_url = [
            poster for poster in posters if '1478w' in poster]
        poster_url = poster_url[0].replace(' 1478w', '')
        print(poster_url)

        if not print_only and episode_index:
            show.season(season_index).episode(episode_index).edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_synopsis,
                "summary.locked": 1,
            })

            if replace_poster:
                show.season(season_index).episode(
                    episode_index).uploadPoster(url=poster_url)

    driver.quit()
