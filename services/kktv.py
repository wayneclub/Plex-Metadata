import re
import orjson
from common.utils import plex_find_lib, text_format


def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False, season_index=1):
    metadata = html_page.find('script', attrs={'type': 'application/ld+json'})
    data = orjson.loads(str(metadata.string))
    title = data['name'].strip()

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    show_synopsis = text_format(data['description'])
    show_poster = data['thumbnailUrl'].replace('.xs', '.lg')

    print(f"\n{title}\n{show_synopsis}\n{show_poster}")

    if not print_only and season_index == 1:
        show.edit(**{
            "summary.value": show_synopsis,
            "summary.locked": 1,
        })

        show.season(season_index).edit(**{
            "title.value": f'第 {season_index} 季',
            "title.locked": 1,
            "summary.value": show_synopsis,
            "summary.locked": 1,
        })

        if replace_poster:
            show.uploadPoster(url=show_poster)
            if 'containsSeason' in data and len(data['containsSeason']) == 1:
                show.season(season_index).uploadPoster(url=show_poster)

    for season in data['containsSeason']:
        season_search = re.search(r'第(\d+)季', season['name'])
        if season_search:
            season_index = int(season_search.group(1))
        for episode in season['episode']:
            episode_search = re.search(r'第\d+季第(\d+)集', episode['name'])
            episode_index = int(episode_search.group(1))

            episode_poster = episode['video']['thumbnailUrl'].replace(
                '.xs', '.lg')

            print(episode_poster)

            if not print_only:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": f'第 {episode_index} 集',
                    "title.locked": 1,
                })
                if replace_poster:
                    show.season(season_index).episode(
                        episode_index).uploadPoster(url=episode_poster)
