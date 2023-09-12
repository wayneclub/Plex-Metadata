import re
from utils.helper import plex_find_lib, text_format, save_html
from utils.dictionary import translate_text


def get_metadata(html_page, plex, plex_title="", print_only=False, season_index=1):
    show = ''
    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title)

    type_1 = html_page.find_all('strong')
    if type_1:
        for tmp in type_1:
            episode_index = ''
            episode_regex = re.search(
                r'第(\d+)集([\-：])*(.+)*', tmp.text)
            if episode_regex:
                episode_index = int(episode_regex.group(1))
                episode_synopsis = episode_regex.group(3)

                if not episode_synopsis:
                    episode_synopsis = tmp.find_next('strong').text

            if episode_index:
                episode_title = f"第 {episode_index} 集"
                print(f"\n{episode_title}\n{episode_synopsis}")

                if not print_only:
                    show.season(season_index).episode(episode_index).edit(**{
                        "title.value": episode_title,
                        "title.locked": 1,
                        "summary.value": episode_synopsis,
                        "summary.locked": 1,
                    })
    else:
        for episode in html_page.find_all('span', text=re.compile('第[0-9]+集')):

            episode_regex = re.search(
                r'第([0-9]+)集([\-：])*(.+)*', episode.text)

            if episode_regex:
                episode_index = int(episode_regex.group(1))
                if episode_regex.group(3):
                    episode_title = text_format(
                        episode_regex.group(3).strip())

                episode_synopsis = text_format(translate_text(episode.parent.find_next(
                    'p').get_text(strip=True)), trim=True)
                # episode_synopsis = episode_synopsis.replace('樸', '朴')
                # episode_synopsis = episode_synopsis.replace('熙載', '熙釮')
                # episode_synopsis = episode_synopsis.replace('道真', '燾珍')
                # episode_synopsis = episode_synopsis.replace('泰梨', '樂園')
                # episode_synopsis = episode_synopsis.replace('賢武', '炫茂')

            if show and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title):
                episode_title = re.sub(
                    r'剧([0-9]+)集', '第 \\1 集', show.season(season_index).episode(episode_index).title)
            else:
                episode_title = f'第 {episode_index} 集'

            print(f"\n{episode_title}\n{episode_synopsis}")

            if not print_only and episode_index:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
