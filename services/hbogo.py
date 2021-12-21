import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from common.utils import plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False):
    title = driver.find_element(
        By.XPATH, "//div[@class='series-title']").text.strip()

    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    episode_list = []
    for season_button in driver.find_elements(By.XPATH, "//div[@class='series-seasons-list']/button"):
        if season_button.is_enabled():
            season_button.click()
            time.sleep(1)

            season_synopsis = text_format(driver.find_element(
                By.XPATH, "//meta[@name='description']").get_attribute('content').replace('本季首播。', '').replace('劇集首播。', ''))
            print(f"\n{season_synopsis}\n")

            web_content = BeautifulSoup(driver.page_source, 'lxml')

            for episode_element in web_content.find('div', class_='series-episode-list').find_all('div', class_='episode-individual'):
                episode_text = episode_element.find(
                    'div', class_='episode-title').get_text(strip=True)
                episode_regex = re.search(r'.+S(\d+)\:(\d+)', episode_text)
                if episode_regex:
                    episode = dict()
                    episode['season_index'] = int(episode_regex.group(1))
                    episode['episode_index'] = int(episode_regex.group(2))
                    episode['episode_title'] = f"第 {episode['episode_index']} 集"

                    if re.search(r'第 [0-9]+ 集', episode['episode_title']) and re.search(r'[\u4E00-\u9FFF]', show.season(episode['season_index']).episode(episode['episode_index']).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(episode['season_index']).episode(episode['episode_index']).title):
                        episode['episode_title'] = text_format(show.season(
                            episode['season_index']).episode(episode['episode_index']).title)

                    episode['url'] = f"https://www.hbogoasia.tw/series/{episode_element.find('img')['id'].replace('episode-image-', '')}"
                    episode_list.append(episode)

                    if episode['season_index'] and episode['episode_index'] == 1 and not print_only:
                        show.season(episode['season_index']).edit(**{
                            "summary.value": season_synopsis,
                            "summary.locked": 1,
                        })

    for episode in episode_list:
        driver.get(episode['url'])
        episode_synopsis = text_format(WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.XPATH, "//div[@class='movie-synopsis']"))).text.replace('本季首播。', ''))
        episode_poster = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
            (By.XPATH, "//img[@class='posterImage']"))).get_attribute('src').strip()
        print(f"\n{episode['episode_title']}\n{episode_synopsis}")
        print(episode_poster)

        if replace_poster:
            show.season(episode['season_index']).episode(
                episode['episode_index']).uploadPoster(url=episode_poster)

        show.season(episode['season_index']).episode(episode['episode_index']).edit(**{
            "title.value": episode['episode_title'],
            "title.locked": 1,
            "summary.value": episode_synopsis,
            "summary.locked": 1,
        })

    driver.quit()
