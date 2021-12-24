import os
import math
import re
from common.utils import compress_image, get_static_html, plex_find_lib, text_format, download_posters


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False):
    series_url = f'https://disney.content.edge.bamgrid.com/svc/content/DmcSeriesBundle/version/5.1/region/TW/audience/false/maturity/1850/language/zh-Hant/encodedSeriesId/{os.path.basename(driver.current_url)}'
    driver.quit()
    data = get_static_html(series_url, True)['data']['DmcSeriesBundle']
    title = data['series']['text']['title']['full']['series']['default']['content']
    show_synopsis = data['series']['text']['description']['medium']['series']['default']['content']

    if 'background_details' in data['series']['image']:
        show_background = data['series']['image']['background_details']['1.78']['series']['default']['url']
    elif 'background' in data['series']['image']:
        show_background = data['series']['image']['background']['1.78']['series']['default']['url']

    print(f"{title}\n{show_synopsis}\n{show_background}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)
        show.edit(**{
            "summary.value": show_synopsis,
            "summary.locked": 1
        })
        if replace_poster:
            show_background_file = compress_image(show_background)
            show.uploadArt(filepath=show_background_file)
            if os.path.exists(show_background_file):
                os.remove(show_background_file)

    posters = set()
    for season in data['seasons']['seasons']:
        season_index = season['seasonSequenceNumber']
        episode_list = check_episodes(season, series_url)
        for episode_id in episode_list:
            episode_url = re.sub(r'(.+)DmcSeriesBundle(.+)encodedSeriesId.+',
                                 '\\1DmcVideo\\2contentId/', series_url) + episode_id
            print(episode_url)
            episode_data = get_static_html(
                episode_url, True)['data']['DmcVideo']['video']
            episode, images = parse_json(episode_data)
            posters = set.union(posters, images)
            episode_index = episode['index']
            if season_index == 1 and episode_index == 1:
                print(episode['show_poster'])
                if not print_only and replace_poster:
                    show_poster_file = compress_image(episode['show_poster'])
                    show.uploadPoster(filepath=show_poster_file)
                    if os.path.exists(show_poster_file):
                        os.remove(show_poster_file)

            if episode_index == 1:
                print(
                    f"\n第 {season_index} 季\n{episode['season_synopsis']}")
                if season_index and not print_only:
                    show.season(season_index).edit(**{
                        "title.value": f'第 {season_index} 季',
                        "title.locked": 1,
                        "summary.value": episode['season_synopsis'],
                        "summary.locked": 1,
                    })

            if re.search(r'^第.+集$', episode['title']):
                episode['title'] = f'第 {episode_index} 集'

            if not re.search(r'^第.+集$', episode['title']):
                print(
                    f"\n第 {episode_index} 集：{episode['title']}\n{episode['synopsis']}\n{episode['poster']}")
            else:
                print(
                    f"\n{episode['title']}\n{episode['synopsis']}\n{episode['poster']}")

            if not print_only and episode_index:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode['title'],
                    "title.locked": 1,
                    "summary.value": episode['synopsis'],
                    "summary.locked": 1,
                })

                if replace_poster:

                    episode_poster_file = compress_image(episode['poster'])
                    show.season(season_index).episode(
                        episode_index).uploadPoster(filepath=episode_poster_file)
                    if os.path.exists(episode_poster_file):
                        os.remove(episode_poster_file)

    print()
    posters.remove(show_background)
    for season_index, poster in enumerate(list(posters)[1:]):
        print(poster)
        if replace_poster:
            season_background_file = compress_image(poster)
            show.season(season_index).uploadArt(
                filepath=season_background_file)
            if os.path.exists(season_background_file):
                os.remove(season_background_file)


def check_episodes(season, series_url):
    episode_num = season['episodes_meta']['hits']
    episodes = season['downloadableEpisodes']
    if len(episodes) != episode_num:
        season_id = season['seasonId']
        page_size = math.ceil(len(episodes) / 15)
        episodes = []
        for page in range(1, page_size+1):
            episode_page_url = re.sub(r'(.+)DmcSeriesBundle(.+)encodedSeriesId.+',
                                      '\\1DmcEpisodes\\2seasonId/', series_url) + f'{season_id}/pageSize/15/page/{page}'
            for episode in get_static_html(episode_page_url, True)['data']['DmcEpisodes']['videos']:
                episodes.append(episode['contentId'])
    return episodes


def parse_json(data):
    episode = dict()
    episode['index'] = data['episodeSequenceNumber']
    episode['title'] = data['text']['title']['full']['program']['default']['content']
    episode['synopsis'] = text_format(
        data['text']['description']['full']['program']['default']['content'])
    episode['season_synopsis'] = text_format(
        data['text']['description']['medium']['season']['default']['content'])

    episode['show_poster'] = data['image']['tile']['0.75']['series']['default']['url']
    episode['poster'] = data['image']['thumbnail']['1.78']['program']['default']['url']
    images = set()
    for image_key in data['image'].keys():
        if not 'title' in image_key and not 'tile' in image_key and '1.78' in data['image'][image_key] and 'series' in data['image'][image_key]['1.78']:
            # print(image_key)
            images.add(data['image'][image_key]['1.78']
                       ['series']['default']['url'])

    return episode, images
