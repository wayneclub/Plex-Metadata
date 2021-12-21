import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from common.utils import plex_find_lib, text_format


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
