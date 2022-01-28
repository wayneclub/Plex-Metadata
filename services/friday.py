import re
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from common.utils import plex_find_lib, text_format, get_dynamic_html
from services.service import Service

class Friday(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

    def get_content_type(self, content_type):
        program = {
            'movie': 1,
            'drama': 2,
            'anime': 3,
            'show': 4
        }

        if program.get(content_type):
            return program.get(content_type)

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
        content_rating = f"tw/{rating}"

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

                print(f"\n第 {episode_index} 集：{episode_title}\n{episode_synopsis}")
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
            r'https:\/\/video\.friday\.tw\/(drama|anime|movie|show)\/detail\/(.+)', self.url)
        content_type = self.get_content_type(content_search.group(1))
        driver = get_dynamic_html(self.url)

        if content_type > 1:
            self.get_show_metadata(driver)
        else:
            self.get_movie_metadata(driver)
