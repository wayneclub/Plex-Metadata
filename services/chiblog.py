import re
from bs4 import BeautifulSoup
from common.utils import plex_find_lib, text_format
from common.dictionary import translate_text


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):
    html_page = BeautifulSoup(driver.page_source, 'lxml')
    driver.quit()
    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title)

    episode_list = html_page.find(
        'div', class_='entry-inner').find_all('span', text=re.compile(r'第\d+集'))
    if len(episode_list) < 6:
        episode_list = []
        for episode in html_page.find(
                'div', class_='entry-inner').find_all('p'):
            episode_regex = episode.find(text=re.compile(r'第\d+集'))
            if episode_regex:
                if isinstance(episode_regex, str):
                    episode_list.append(episode_regex.parent)
                else:
                    episode_list.append(episode_regex)

    for episode in episode_list:
        # print(episode)
        episode_regex = re.search(
            r'第([0-9]+)集', episode.get_text(strip=True))
        if episode_regex:
            episode_index = int(episode_regex.group(1))

        if re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title):
            episode_title = re.sub(
                r'剧([0-9]+)集', '第 \\1 集', show.season(season_index).episode(episode_index).title)
        else:
            episode_title = f'第 {episode_index} 集'

        if episode.next_sibling and isinstance(episode.next_sibling, str) and episode.next_sibling == '－':
            episode_title = text_format(
                episode.next_sibling.find_next('span').get_text(strip=True))

        if episode.next_sibling and episode.next_sibling.name == 'span' and not re.search(r'（(大)*結局）', episode.next_sibling.text):
            episode_synopsis = text_format(
                episode.next_sibling.get_text(strip=True))
        elif episode.next_sibling and episode.next_sibling.name == 'br':
            episode_synopsis = text_format(
                episode.next_sibling.next_sibling)
        # elif episode.next_sibling and isinstance(episode.next_sibling, str):
        #     if episode.next_sibling.next.name == 'span':
        #         episode_synopsis = text_format(
        #             episode.next_sibling.find_next('span').get_text(strip=True))
        #     else:
        #         episode_synopsis = text_format(episode.next_sibling)

        if episode.parent.next_sibling.name == 'div' or episode.parent.next_sibling.name == 'p':
            episode_synopsis = text_format(
                episode.parent.next_sibling.get_text(strip=True))

        episode_synopsis = translate_text(episode_synopsis)

        print(f"\n{episode_title}\n{episode_synopsis}")

        if not print_only and episode_index:
            show.season(season_index).episode(episode_index).edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_synopsis,
                "summary.locked": 1,
            })
