import re
from bs4 import BeautifulSoup
import orjson
from common.utils import plex_find_lib, text_format, get_static_html


def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False, season_index=1):
    metadata = html_page.find('script', attrs={'type': 'application/ld+json'})
    data = orjson.loads(str(metadata.string))
    title = data['name'].strip()
    genre = data['genre'][0]
    if '劇' in genre:
        if not print_only:
            show = plex_find_lib(plex, 'show', plex_title, title)

        show_synopsis = text_format(
            data['description'].replace(f'《{title}》', ''))
        show_poster = data['image']

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
                show.season(season_index).uploadPoster(url=show_poster)

        for episode in html_page.find('ul', class_='tabVideoList').findAll('a'):
            episode_poster = episode.parent.find('img', class_='photo')['src']
            episode_search = re.search('第(.+)集', episode.get_text(strip=True))
            if episode_search:
                episode_index = int(episode_search.group(1))
                episode_page = get_static_html(
                    f"https://www.myvideo.net.tw{episode['href']}")
                episode_data = orjson.loads(str(episode_page.find(
                    'script', attrs={'type': 'application/ld+json'}).string))
                episode_synopsis = text_format(
                    episode_data['description'].replace(f'《{title} 第{episode_index}集》', ''))

                print(
                    f"\n第 {episode_index} 集\n{episode_synopsis}\n{episode_poster}")

                if not print_only:
                    show.season(season_index).episode(episode_index).edit(**{
                        "title.value": f'第 {episode_index} 集',
                        "title.locked": 1,
                        "summary.value": episode_synopsis,
                        "summary.locked": 1,
                    })
                    if replace_poster:
                        show.season(season_index).episode(
                            episode_index).uploadPoster(url=episode_poster)

    else:
        if not print_only:
            movie = plex_find_lib(plex, 'movie', plex_title, title)

        movie_synopsis = text_format(data['description'])
        movie_poster = data['image']

        match = re.search(r'"rating": \'(.+)\'', str(html_page))

        content_rating = ''
        if match and match.group(1):
            content_rating = f"tw/{match.group(1).strip()}"

        print(f"\n{title}\n{movie_synopsis}\n{content_rating}\n{movie_poster}")

        if not print_only:
            movie.edit(**{
                "contentRating.value": content_rating,
                "contentRating.locked": 1,
                "summary.value": movie_synopsis,
                "summary.locked": 1,
            })
            if replace_poster:
                movie.uploadPoster(url=movie_poster)
