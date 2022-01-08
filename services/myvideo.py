import re
from bs4 import BeautifulSoup
from common.utils import plex_find_lib, text_format


def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False):

    title = html_page.find('div', class_='title').get_text(strip=True)
    print(f"\n{title}")

    if not print_only:
        movie = plex_find_lib(plex, 'movie', plex_title, title)

    moive_info = html_page.find('div', class_='infoArea')
    content_rating = f"tw/{moive_info.find('span', text=re.compile(r'.+級')).get_text(strip=True)}"
    print(f"{content_rating}\n")

    movie_synopsis = text_format(moive_info.find(
        'p', class_='discript').get_text(strip=True))
    print(movie_synopsis + '\n')

    poster_url = html_page.find(
        'section', class_='photoArea').find(
        'img', class_='photo')['src']

    if not print_only and replace_poster:
        movie.edit(**{
            "contentRating.value": content_rating,
            "contentRating.locked": 1,
            "summary.value": movie_synopsis,
            "summary.locked": 1,
        })
        movie.uploadPoster(url=poster_url)
