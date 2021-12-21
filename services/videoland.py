import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from common.utils import plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):
    title = driver.title.replace('緯來日本台-', '')
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    select = driver.find_elements(By.XPATH, "//select[@name='sno']")
    if select:
        select = Select(select[0])
        options = select.options
        for episode_index in range(1, len(options)):
            select = Select(driver.find_element(By.NAME, 'sno'))
            select.select_by_index(episode_index)
            html_page = BeautifulSoup(driver.page_source, 'lxml')
            episode_title = f'第 {episode_index} 集'

            if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                episode_title = show.season(
                    season_index).episode(episode_index).title

            if html_page.find('span', text=re.compile(r'第.+集')):
                episode_synopsis = html_page.find('span', text=re.compile(
                    r'第.+集')).parent.find_all('br')[-1].next_sibling.strip()

                if not episode_synopsis:
                    episode_synopsis = html_page.find('span', text=re.compile(
                        r'第.+集')).parent.find_all('span')[-1].get_text(strip=True)
            else:
                episode_synopsis = html_page.find('div', id='content_body').find(
                    'span').next_sibling.next_sibling.next_sibling.next_sibling

            episode_synopsis = text_format(re.sub(
                r'（[^）]+飾）', '', episode_synopsis.replace('(', '（').replace(')', '）')))
            print(f"\n{episode_title}\n{episode_synopsis}")
            if not print_only and episode_index:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
    else:
        episode_url_list = [episode.get_attribute('href') for episode in driver.find_elements(
            By.XPATH, "//ul[@class='dropdown-menu']/li/a")]
        for episode_index, episode in enumerate(episode_url_list, start=1):
            driver.execute_script(episode)
            episode_title = f'第 {episode_index} 集'
            html_page = BeautifulSoup(driver.page_source, 'lxml')
            episode_synopsis = text_format(re.sub(
                r'（[^）]+飾）', '', html_page.find('h3').next_sibling.replace('(', '（').replace(')', '）')))
            print(f"\n{episode_title}\n{episode_synopsis}")

            if not print_only and episode_index:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
    driver.quit()
