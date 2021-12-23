import re
import json
from common.utils import get_static_html, plex_find_lib, text_format, save_html


def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False):

    title = html_page.find(
        'h1', attrs={'data-testid': 'title-art'}).find('img')['alt'].strip()
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    season_data = json.loads(html_page.find_all(
        'script', attrs={'type': 'text/template'})[-2].string)
    season_keys = season_data['props']['state']['detail']['detail'].keys()

    for season_index, season_key in enumerate(season_keys, start=1):
        season_url = f'https://www.amazon.com/-/zh_TW/gp/video/detail/{season_key}/ref=atv_dp_season_select_s{season_index}?language=zh_TW'
        data = json.loads(get_static_html(season_url).find_all(
            'script', attrs={'type': 'text/template'})[-1].string)
        title_info = data['props']['state']['detail']['btfMoreDetails'][season_key]

        season_index = title_info['seasonNumber']
        season_title = f'第 {season_index} 季'
        season_synopsis = text_format(title_info['synopsis'])
        season_background = title_info['images']['heroshot']

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
                if len(season_keys) == 1:
                    show.uploadArt(url=season_background)
                show.season(season_index).uploadArt(url=season_background)

        episode_data = json.loads(get_static_html(season_url).find_all(
            'script', attrs={'type': 'text/template'})[-1].string)
        parent_id = episode_data['props']['state']['pageTitleId']
        episode_keys = episode_data['props']['state']['collections'][parent_id][0]['titleIds']

        for episode_key in episode_keys:
            episode = episode_data['props']['state']['detail']['detail'][episode_key]
            episode_index = episode['episodeNumber']
            episode_title = episode['title']
            episode_synopsis = episode['synopsis']
            episode_poster = episode['images']['packshot']

            print(
                f"\n第 {episode_index} 集：{episode_title}\n{episode_synopsis}\n{episode_poster}")

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
