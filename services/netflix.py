import re
from common.utils import plex_find_lib, text_format
from common.dictionary import translate_text


def get_metadata(html_page, plex, plex_title="", replace_poster="", print_only=False, season_index=1, change_poster_only=False, translate=False):
    title = html_page.find(
        'h1', class_='title-title').get_text(strip=True)
    if translate:
        title = translate_text(title)
    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    show_synopsis = text_format(html_page.find(
        'div', class_='title-info-synopsis').get_text(strip=True))
    if translate:
        show_synopsis = translate_text(show_synopsis)

    show_background = html_page.find(
        'picture', class_='hero-image-loader').find_all('source')[-1]['srcset']

    if show and not print_only and not change_poster_only and season_index == 1:
        show.edit(**{
            "summary.value": show_synopsis,
            "summary.locked": 1,
        })
        if replace_poster:
            show.uploadArt(url=show_background)

    for season in html_page.find_all('div', class_='season'):

        season_synopsis = text_format(season.find(
            'p', class_='season-synopsis').get_text(strip=True))
        if translate:
            season_synopsis = translate_text(season_synopsis)
        print(f"\n{season_synopsis}\n")

        episode_list = season.find_all('div', class_='episode')

        multi_episode = False

        for episode in episode_list:

            episode_text = episode.find(
                'img', class_='episode-thumbnail-image')['alt']
            episode_text = episode_text.replace('。。', '。').split('。')

            if len(episode_text) > 1:
                episode_num = episode_text[1]

                episode_regex = re.search(
                    r'第 ([0-9]+) 季第 ([0-9]+) 集', episode_num)
                if episode_regex:
                    season_index = int(episode_regex.group(1))
                    episode_index = int(episode_regex.group(2))
                    episode_title = (episode_text[0][2:]).strip()
                else:
                    episode_regex = re.search(
                        r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
                    if episode_regex:
                        season_index = int(episode_regex.group(2))
                        episode_index = int(episode_regex.group(1))
                        episode_title = f'第 {episode_index} 集'
            else:
                episode_num = episode_text[0].replace(
                    '播放“', '').replace('”', '')
                episode_regex = re.search(
                    r'Episode ([0-9]+) of Season ([0-9]+)\.', episode_num)
                if episode_regex:
                    season_index = int(episode_regex.group(2))
                    episode_index = int(episode_regex.group(1))
                episode_title = (episode_num).strip()
                if not re.search(r'[\u4E00-\u9FFF]', episode_title):
                    episode_title = f'第 {episode_index} 集'

            print(episode_num)

            # if season_index == 1 and (episode_index == 9 or episode_index == 10):
            #     break

            if 2 * len(episode_list) == show.season(season_index).leafCount:
                multi_episode = True

            if translate:
                episode_title = translate_text(episode_title)

            if re.search(r'第 [0-9]+ 集', episode_title) and re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title) and not re.search(r'^[剧第]([0-9 ]+)集$', show.season(season_index).episode(episode_index).title):
                episode_title = show.season(
                    season_index).episode(episode_index).title

            if episode_title:
                print(f"{episode_title}\n")

            episode_synopsis = text_format(
                episode.find('p').get_text(strip=True))

            if translate:
                episode_synopsis = translate_text(episode_synopsis)

            print(f"{episode_synopsis}\n")

            episode_img = episode.find(
                'img', class_='episode-thumbnail-image')['src']

            print(f"{episode_img}\n")
            # season_index = 2

            if season_index and episode_index == 1 and not change_poster_only and not print_only:
                show.season(season_index).edit(**{
                    "title.value": f'第 {season_index} 季',
                    "title.locked": 1,
                    "summary.value": season_synopsis,
                    "summary.locked": 1,
                })

            # if season_index == 2:
                # episode_index = episode_index - show.season(1).leafCount
            # elif season_index == 3:
            #     episode_index = episode_index - \
            #         (show.season(1).leafCount + show.season(2).leafCount)
            # elif season_index == 4:
            #     season_index = 3
            #     episode_index = episode_index - \
            #         (show.season(1).leafCount + show.season(2).leafCount)
            # elif season_index == 5:
            #     season_index = 4
            #     episode_index = episode_index - \
            #         (show.season(1).leafCount +
            #          show.season(2).leafCount + show.season(3).leafCount)

            if season_index and episode_index and not print_only:
                if multi_episode:
                    if replace_poster:
                        show.season(season_index).episode(
                            2*episode_index-1).uploadPoster(url=episode_img)
                        show.season(season_index).episode(
                            2*episode_index).uploadPoster(url=episode_img)
                    if re.search(r'第 \d+ 集', episode_title):
                        episode_title_1 = f'第 {2*episode_index-1} 集'
                        episode_title_2 = f'第 {2*episode_index} 集'
                    else:
                        episode_title_1 = episode_title
                        episode_title_2 = episode_title

                    if not change_poster_only:
                        show.season(season_index).episode(2*episode_index-1).edit(**{
                            "title.value": episode_title_1,
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
                        show.season(season_index).episode(2*episode_index).edit(**{
                            "title.value": episode_title_2,
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
                else:
                    if replace_poster:
                        show.season(season_index).episode(
                            episode_index).uploadPoster(url=episode_img)

                    if not change_poster_only:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": episode_title,
                            "title.locked": 1,
                            "summary.value": episode_synopsis,
                            "summary.locked": 1,
                        })
