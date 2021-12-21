import re
from bs4 import BeautifulSoup
from common.utils import plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", print_only=False):
    html_page = BeautifulSoup(driver.page_source, 'lxml')
    driver.quit()

    moive_info = html_page.find('header', class_='movie-header')

    title = moive_info.find('h1').get_text(strip=True)
    print(f"\n{title}")

    if not print_only:
        movie = plex_find_lib(plex, 'movie', plex_title, title)

    content_rating = f"tw/{moive_info.find('span', class_='badge').get_text(strip=True)}"
    print(f"{content_rating}\n")

    movie_synopsis = text_format(moive_info.find('p').get_text(strip=True))
    print(movie_synopsis + '\n')

    image = html_page.find(
        'picture', class_='we-artwork we-artwork--downloaded we-artwork--fullwidth')

    poster_url = ''
    for poster in image.find_all('source'):
        find_poster = re.search(r' (https://.+536x0w.webp)', poster['srcset'])
        if find_poster:
            poster_url = find_poster.group(1)
            print(poster_url)

    if not print_only:
        movie.edit(**{
            "contentRating.value": content_rating,
            "contentRating.locked": 1,
            "summary.value": movie_synopsis,
            "summary.locked": 1,
        })
        movie.uploadPoster(url=poster_url)
