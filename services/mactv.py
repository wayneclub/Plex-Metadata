import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from common.utils import get_dynamic_html, plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):
    title = driver.find_element(
        By.XPATH, "//h1").text.split('分集劇情介紹')[0].strip()

    if len(driver.find_elements(By.XPATH, "//a[contains(text(), '共')]")) > 0:
        page_regex = re.search(
            r'共([0-9]+)頁:', driver.find_element(By.XPATH, "//a[contains(text(), '共')]").text)
        if page_regex:
            total_pages = page_regex.group(1)

        current_page = driver.find_element(
            By.XPATH, "//li[@class='thisclass']").text

        if current_page == '1':
            print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)
        title = show.title

    html_page = BeautifulSoup(driver.page_source, 'lxml')

    for episode in html_page.find_all('p', text=re.compile('第[0-9]+集')):

        episode_regex = re.search(
            r'第([0-9]+)集[：\- ]*(.+)*', episode.get_text(strip=True))
        if episode_regex:
            episode_index = int(episode_regex.group(1))

        if re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title):
            episode_title = re.sub(
                r'剧([0-9]+)集', '第 \\1 集', show.season(season_index).episode(episode_index).title)

        if episode_regex.group(2):
            episode_title = text_format(episode_regex.group(2))
        else:
            episode_title = f'第 {episode_index} 集'

        episode_synopsis = text_format(episode.find_next_sibling('p').text)

        print(f"\n{episode_title}\n{episode_synopsis}")

        if not print_only and episode_index:
            show.season(season_index).episode(episode_index).edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_synopsis,
                "summary.locked": 1,
            })

    if not print_only and current_page and current_page != total_pages:
        next_page_url = driver.find_element(By.XPATH,
                                            "//a[text()='下一頁']").get_attribute('href')
        get_metadata(get_dynamic_html(next_page_url),
                     plex, title, print_only, season_index)
    else:
        driver.quit()
