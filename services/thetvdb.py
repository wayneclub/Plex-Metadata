import re
import time
from selenium.webdriver.common.by import By
from utils.helper import plex_find_lib, get_static_html, text_format
from utils.dictionary import translate_text, convert_chinese_number


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False, season_index=1):
    if len(driver.find_elements(By.XPATH,
                                "//div[@class='change_translation_text'][@data-language='zhtw']")) > 0:
        title = driver.find_element(By.XPATH,
                                    "//div[@class='change_translation_text'][@data-language='zhtw']").get_attribute('data-title')
    elif len(driver.find_elements(By.XPATH,
                                  "//div[@class='change_translation_text'][@data-language='zho']")) > 0:
        title = driver.find_element(By.XPATH,
                                    "//div[@class='change_translation_text'][@data-language='zho']").get_attribute('data-title')
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    season_url = f'{driver.current_url}/seasons/official/{season_index}'
    print(f"\n第 {season_index} 季")

    driver.get(season_url)
    time.sleep(1)

    for episode in driver.find_elements(By.XPATH, '//tr')[1:]:
        cells = episode.find_elements(
            By.TAG_NAME, 'td')
        episode_regex = re.search(
            r'S([0-9]+)E([0-9]+)', cells[0].text)
        episode_index = int(episode_regex.group(2))
        episode_url = cells[1].find_element(
            By.TAG_NAME, 'a').get_attribute('href')

        html_page = get_static_html(episode_url)

        episode_detail = ''
        if html_page.find('div', {'data-language': 'zhtw'}):
            episode_detail = html_page.find('div', {'data-language': 'zhtw'})
        elif html_page.find('div', {'data-language': 'zho'}):
            episode_detail = html_page.find('div', {'data-language': 'zho'})
        elif html_page.find('div', {'data-language': 'yue'}):
            episode_detail = html_page.find('div', {'data-language': 'yue'})

        if episode_detail:
            episode_title = episode_detail['data-title'].strip()
            episode_synopsis = episode_detail.get_text(strip=True)
            # print('episode_title', episode_title)
            # print('episode_synopsis', episode_synopsis)
            if episode_title and episode_synopsis:
                if re.search(r'^第[0-9 ]+集$', episode_title):
                    episode_title = f'第 {episode_index} 集'
                elif re.search(r'^第.+集$', episode_title):
                    episode_number = int(convert_chinese_number(
                        episode_title.replace('第', '').replace('集', '').strip()))
                    episode_title = f'第 {episode_number} 集'
                else:
                    episode_title = re.sub(
                        r'第[0-9 ]+集.+', '', episode_title).strip()
                episode_synopsis = text_format(
                    episode_synopsis)
            elif episode_title and not episode_synopsis:
                if re.search(r'^第[0-9 ]+集$', episode_title):
                    episode_title = f'第 {episode_index} 集'
                else:
                    episode_title = text_format(episode_title)
                episode_synopsis = ''
            else:
                episode_title = f'第 {episode_index} 集'
                episode_synopsis = text_format(episode_synopsis)

            if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                episode_title = show.season(
                    season_index).episode(episode_index).title

            if not episode_synopsis and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).summary):
                episode_synopsis = text_format(show.season(
                    season_index).episode(episode_index).summary)

            print(f"\n{episode_title}\n{episode_synopsis}")

            if not print_only and episode_index:

                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })

        if not print_only and episode_index:
            if html_page.find('a', class_='thumbnail'):
                episode_poster = html_page.find(
                    'a', class_='thumbnail').find('img')['src']
                if replace_poster and episode_poster:
                    show.season(season_index).episode(
                        episode_index).uploadPoster(url=episode_poster)

    driver.quit()
