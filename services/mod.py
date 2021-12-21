import re
from bs4 import BeautifulSoup
from common.utils import plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):

    html_page = BeautifulSoup(driver.page_source, 'lxml')
    driver.quit()
    title = html_page.find(
        'h3', class_='heading-area__title--regular').get_text(strip=True)
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    for episode in html_page.find_all('div', class_='port-card__overlay overlay-card'):

        episode_title = episode.find('h5').get_text(
            strip=True).replace(title, '').replace('(完)', '').replace('第', '第 ').replace('集', ' 集').strip()
        episode_regex = re.search(r'第([0-9]+)', episode_title)
        if episode_regex:
            episode_index = int(episode_regex.group(1))

        episode_synopsis = text_format(
            re.sub(r'\(.+\)', '', episode.find('p').get_text(strip=True)))

        if episode_synopsis[-1] == '，':
            episode_synopsis = episode_synopsis.replace('，', '…')
        elif episode_synopsis[-1] != '。' and episode_synopsis[-1] != '？' and episode_synopsis[-1] != '！':
            episode_synopsis = episode_synopsis + '…'

        print(f"\n{episode_title}\n{episode_synopsis}")

        if not print_only and episode_index:
            show.season(season_index).episode(episode_index).edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_synopsis,
                "summary.locked": 1,
            })
