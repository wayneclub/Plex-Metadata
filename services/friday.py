import re
import sys
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.helper import plex_find_lib, text_format, get_dynamic_html
from services.service import Service


class Friday(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        self.api ={
            'pic': 'https://vbmspic.video.friday.tw',
            'title' : 'https://video.friday.tw/api2/content/get?contentId={content_id}&contentType={content_type}&srcRecommendId=-1&recommendId=&eventPageId=&offset=0&length=1',
            'episode_list' : 'https://video.friday.tw/api2/episode/list?contentId={content_id}&contentType={content_type}&offset=0&length=100&mode=2',
        }

    def get_content_type(self, content_type):
        program = {
            'movie': 1,
            'drama': 2,
            'anime': 3,
            'show': 4
        }

        if program.get(content_type):
            return program.get(content_type)

    def get_content_rating(self, rating):
        content_rating = {
            '普': '普遍級',
            '保': '保護級',
            '輔12+': '輔12級',
            '輔15+': '輔15級',
            '限': '限制級'
        }

        if content_rating.get(rating):
            return content_rating.get(rating)

    def movie_metadata(self, data):
        print()

    def series_metadata(self, data):

        title = re.sub(r'(.+?)(第.+[季|彈])*', '\\1', data['chineseName']).strip()
        season_regex = re.search(r'.+第([0-9]+)季', title)
        if season_regex:
            season_index = int(season_regex.group(1))
        else:
            season_index = 1

        show_poster = self.api['pic'] + data['imageUrl']

        original_title = data['englishName'].replace('，', ',')

        print(f"\n{title}\n{show_poster}")

        episode_list_url = self.api['episode_list'].format(
            content_id=data['contentId'], content_type=data['contentType'])
        self.logger.debug(episode_list_url)

        res = self.session.get(url=episode_list_url, timeout=5)

        if res.ok:
            data = res.json()['data']

            if not self.print_only:
                show = plex_find_lib(self.plex, 'show', self.plex_title, title)

                show.season(season_index).edit(**{
                    "title.value": f'第 {season_index} 季',
                    "title.locked": 1,
                })

                if self.replace_poster:
                    show.uploadPoster(url=show_poster)
                    if season_index == 1:
                        show.season(season_index).uploadPoster(url=show_poster)

            for episode in data['episodeList']:
                episode_index = int(episode['sort'])
                episode_background = self.api['pic'] + episode['stillImageUrl']
                episode_title = episode['separationName']
                episode_synopsis = episode['separationIntroduction']

                if episode_title:
                    print(f"\n第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_background}")
                else:
                    print(f"\n第 {episode_index} 集：{episode_synopsis}\n{episode_background}")

                if not self.print_only and episode_index:
                    if episode_title:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": episode_title,
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
                    else:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": f'第 {episode_index} 集',
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })

        else:
            self.logger.error(res.text)




    def get_movie_metadata(self, driver):
        title = driver.find_element(By.XPATH, "//h1[@class='title-chi']").text
        movie_synopsis = text_format(
            driver.find_element(By.XPATH, "//p[contains(@class, 'storyline')]").text)

        movie_poster = driver.find_element(
            By.XPATH, "//div[@class='order-poster']/img").get_attribute('src').replace('_S', '').replace('_M', '')
        if not movie_poster:
            movie_poster = driver.find_elements(
                By.XPATH, "//div[@class='photos-content']/img")[-1].get_attribute('src').replace('_S', '').replace('_M', '')

        rating = driver.find_element(By.XPATH, "//span[@class='grading']").text
        content_rating = f"tw/{self.get_content_rating(rating)}"

        print(f"\n{title}\t{content_rating}\n{movie_synopsis}\n{movie_poster}")

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

    def get_show_metadata(self, driver):

        title = driver.find_element(By.XPATH, "//h1[@class='title-chi']").text

        season_regex = re.search(r'.+第([0-9]+)季', title)
        if season_regex:
            season_index = int(season_regex.group(1))
        else:
            season_index = 1

        season_synopsis = text_format(
            driver.find_element(By.XPATH, "//p[contains(@class, 'storyline')]").text)

        show_poster = driver.find_element(
            By.XPATH, "//div[@class='order-poster']/img").get_attribute('src').replace('_S', '').replace('_M', '')
        if not show_poster:
            show_poster = driver.find_elements(
                By.XPATH, "//div[@class='photos-content']/img")[-1].get_attribute('src').replace('_S', '').replace('_M', '')

        print(f"\n{title}\n{season_synopsis}\n{show_poster}")

        if not self.print_only:
            show = plex_find_lib(self.plex, 'show', self.plex_title, title)

            show.season(season_index).edit(**{
                "title.value": f'第 {season_index} 季',
                "title.locked": 1,
                "summary.value": season_synopsis,
                "summary.locked": 1,
            })

            if self.replace_poster:
                show.uploadPoster(url=show_poster)
                if season_index == 1:
                    show.season(season_index).uploadPoster(url=show_poster)

        action = ActionChains(driver)
        for li in driver.find_elements(By.XPATH, "//ul[@class='episode-container']/li"):
            action.move_to_element(li).perform()
            wait = WebDriverWait(driver, 0.5)
            episode_content = wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'episode-content')))

            episode_title = episode_content.find_element(By.CLASS_NAME,
                                                         'epi-title').text
            episode_synopsis = text_format(
                episode_content.find_element(By.CLASS_NAME, 'epi-info').text)

            season_episode_regex = re.search(r'(第([0-9]+)季)*([0-9]+)', li.text)

            if season_episode_regex:
                if season_episode_regex.group(1):
                    season_index = int(season_episode_regex.group(2))
                    episode_index = int(season_episode_regex.group(3))
                else:
                    episode_index = int(li.text)

                if episode_index == 1:
                    print(f"\n第 {season_index} 季")

                print(
                    f"\n第 {episode_index} 集：{episode_title}\n{episode_synopsis}")
            else:
                print(f"\n{li.text} {episode_title}\n{episode_synopsis}")

            if not self.print_only and episode_index:
                if episode_title:
                    show.season(season_index).episode(episode_index).edit(**{
                        "title.value": episode_title,
                        "title.locked": 1,
                        "summary.value": episode_synopsis,
                        "summary.locked": 1,
                    })
                else:
                    show.season(season_index).episode(episode_index).edit(**{
                        "title.value": f'第 {episode_index} 集',
                        "title.locked": 1,
                        "summary.value": episode_synopsis,
                        "summary.locked": 1,
                    })
        driver.quit()

    def main(self):
        content_search = re.search(
            r'(https:\/\/video\.friday\.tw\/(drama|anime|movie|show)\/detail\/(\d+))', self.url)

        content_type = self.get_content_type(content_search.group(2))
        content_id = content_search.group(3)
        # driver = get_dynamic_html(self.url)

        title_url = ''

        title_url = self.api['title'].format(
            content_id=content_id, content_type=content_type)
        res = self.session.post(title_url, timeout=5)
        if res.ok:
            data = res.json()
            if data.get('data'):
                data = data['data']['content']
            else:
                self.logger.error(data['message'])
                sys.exit(1)

            if content_type == 1:
                self.movie_metadata(data)
            else:
                self.series_metadata(data)

        # if content_type > 1:
        #     self.get_show_metadata(driver)
        # else:
        #     self.get_movie_metadata(driver)

