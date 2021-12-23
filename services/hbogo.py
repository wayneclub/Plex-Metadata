import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from common.utils import plex_find_lib, get_static_html, text_format


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False):
    title = driver.find_element(
        By.XPATH, "//div[@class='series-title']").text.strip()

    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    parent_id_regex = re.search(
        r'https:\/\/www.hbogoasia.tw\/series\/sr(\d+)', driver.current_url)
    parent_id = parent_id_regex.group(1)
    parent_url = f'https://api2.hbogoasia.com/v1/tvseason/list?parentId={parent_id}&territory=TWN'

    driver.quit()
    season_list = get_static_html(parent_url, True)['results']
    for season in season_list:
        season_index = season['seasonNumber']
        season_url = f"https://api2.hbogoasia.com/v1/tvepisode/list?parentId={season['contentId']}&territory=TWN"
        season_title = f'第 {season_index} 季'

        for image in season['materials']:
            if 'largescreen_thumbnail' in image['href']:
                season_background = image['href']
            if 'portrait' in image['href']:
                show_poster = image['href']
        season_synopsis = text_format(next((title_info['summary'] for title_info in season['metadata']['titleInformations']
                                            if title_info['lang'] == 'CHN')))
        if not re.search(r'[\u4E00-\u9FFF]', season_synopsis):
            season_synopsis = text_format(show.season(season_index).summary)

        print(f"\n{season_title}\n{season_synopsis}\n{season_background}")

        if season_index and not print_only:
            if season_index == 1 and re.search(r'[\u4E00-\u9FFF]', season_synopsis):
                show.edit(**{
                    "summary.value": season_synopsis,
                    "summary.locked": 1,
                })
            show.season(season_index).edit(**{
                "title.value": season_title,
                "title.locked": 1,
                "summary.value": season_synopsis,
                "summary.locked": 1,
            })
            if replace_poster:
                if len(season_list) == 1:
                    show.uploadArt(url=season_background)
                show.season(season_index).uploadArt(url=season_background)

        for episode in get_static_html(season_url, True)['results']:
            episode_index = episode['episodeNumber']

            episode_title = f'第 {episode_index} 集'

            episode_synopsis = text_format(next((title_info['description'] for title_info in episode['metadata']['titleInformations']
                                                 if title_info['lang'] == 'CHN')))

            episode_poster = episode['image']

            if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                episode_title = text_format(show.season(
                    season_index).episode(episode_index).title)

            print(
                f"\n{episode_title}\n{episode_synopsis}\n{episode_poster}")

            if season_index and episode_index and not print_only:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
                if replace_poster:
                    show.season(season_index).episode(
                        episode_index).uploadPoster(url=episode_poster)
