import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from utils.helper import plex_find_lib, text_format
from utils.dictionary import translate_text


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):
    html_page = BeautifulSoup(driver.page_source, 'lxml')
    title = html_page.find('h1').get_text(strip=True)
    print(title)
    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    for episode_link in driver.find_elements(By.XPATH, "//div[@class='pagers']/a"):
        episode_link.click()
    html_page = BeautifulSoup(driver.page_source, 'lxml')
    for episode in html_page.find('ul', class_='dramaSerialList').find_all('dt'):
        episode_regex = re.search(
            r'第(\d+)集', episode.get_text(strip=True))
        episode_index = int(episode_regex.group(1))
        episode_title = f'第 {episode_index} 集'

        if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
            episode_title = show.season(
                season_index).episode(episode_index).title

        episode_synopsis = text_format(translate_text(
            episode.find_next('dd').get_text(strip=True)), trim=True)

        print(f"\n{episode_title}\n{episode_synopsis}")

        if not print_only and episode_index:
            show.season(season_index).episode(episode_index).edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_synopsis,
                "summary.locked": 1,
            })

    driver.quit()
