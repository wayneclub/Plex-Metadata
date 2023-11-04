"""
This module is to get Netflix, HBOGo, Friday, iTune, etc metadata and automatically apply to Plex.

"""
from __future__ import annotations
import argparse
import logging
from datetime import datetime
import os
from pathlib import Path
import re
from objects.titles import Title, Titles
from services import service_map
from services.baseservice import BaseService
from utils.collections import as_list
from utils.helper import autocrop, check_url_exist
from utils.io import load_toml
from utils.plex import Plex
from configs.config import app_name, __version__, directories, filenames


def main() -> None:
    parser = argparse.ArgumentParser(
        description='取得Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等電影、影集資訊')

    parser.add_argument(
        'url', help='Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等介紹網址')

    parser.add_argument('-t', '--title', dest='plex_title', help='plex 標題')

    parser.add_argument('-i', '--input_summary',
                        dest='input_summary', help='劇情檔案')

    parser.add_argument('-r', '--replace', dest='replace',
                        nargs='?', const=True, help='取代標題')

    parser.add_argument('-rp', '--replace_poster', dest='replace_poster',
                        nargs='?', const=True, help='取代標題')

    parser.add_argument('-print', '--print_only', dest='print_only',
                        nargs='?', const=True, help='只印出不要更新')

    parser.add_argument('-s',
                        '--season',
                        dest='season',
                        help="download season [0-9]")
    parser.add_argument('-e',
                        '--episode',
                        dest='episode',
                        help="download episode [0-9]")

    parser.add_argument('-region', '--region', dest='region', help='詮釋資料地區')

    parser.add_argument('-download', '--download_poster', dest='download_poster',
                        nargs='?', const=True, help='下載海報')

    parser.add_argument('-p',
                        '--proxy',
                        dest='proxy',
                        nargs='?',
                        help="proxy")

    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help="enable debug logging",
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='{app_name} {version}'.format(
            app_name=app_name, version=__version__)
    )

    args = parser.parse_args()

    if args.debug:
        os.makedirs(directories.logs, exist_ok=True)
        log_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file_path = str(filenames.log).format(
            app_name=app_name, log_time=log_time)
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(log_file_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            format='%(message)s',
            level=logging.INFO,
        )

    service = next((service for service in service_map
                   if service['domain'] in args.url), None)

    if service:
        service_config = load_toml(
            str(filenames.config).format(service=service['name']))
        args.service = service
        args.config = service_config
        service: BaseService = service['class'](args)

        log = service.log

        log.info(f" + Loaded [{service.source}] Class instance")

        log.info("Retrieving Titles")
        titles = Titles(as_list(service.get_titles()))
        if not titles:
            log.exit(" - No titles returned!")

        titles.order()
        titles.print()

        plex = None
        if args.replace or args.replace_poster:
            plex = Plex()

        for title in titles.with_wanted(service.download_season, service.download_episode):
            if title.type == Title.Types.TV:
                log.info(
                    f"{title.name} S{(title.season or 0):02}E{(title.episode or 0):02}{' - ' + title.episode_name if title.episode_name else ''}")

                if title.episode_synopsis:
                    log.info(title.episode_synopsis)

                if title.episode_poster:
                    log.info(title.episode_poster)

                if plex:
                    show = plex.plex_find_lib(
                        'show', args.plex_title, title.name)
                    if title.synopsis:
                        show.edit(**{
                            "summary.value": title.synopsis,
                            "summary.locked": 1
                        })
                    if title.content_rating:
                        show.edit(**{
                            "contentRating.value": title.content_rating,
                            "contentRating.locked": 1,
                        })
                    if args.replace_poster and check_url_exist(title.poster, service.session):
                        show.uploadPoster(url=title.poster)

                    show.season(title.season).edit(**{
                        "title.value": title.season_name if title.season_name else f'第 {title.season} 季',
                        "title.locked": 1,
                    })

                    if title.season_synopsis:
                        show.season(title.season).edit(**{
                            "summary.value": title.season_synopsis,
                            "summary.locked": 1,
                        })

                    plex_episode_title = show.season(
                        title.season).episode(title.episode).title

                    if title.episode_name and re.search(r'^[剧第]([0-9 ]+)集$', plex_episode_title):
                        show.season(title.season).episode(title.episode).edit(**{
                            "title.value": title.episode_name,
                            "title.locked": 1,
                        })
                    else:
                        show.season(title.season).episode(title.episode).edit(**{
                            "title.value": title.episode_name if title.episode_name else f'第 {title.episode} 集',
                            "title.locked": 1,
                        })

                    if title.episode_synopsis:
                        show.season(title.season).episode(title.episode).edit(**{
                            "summary.value": title.episode_synopsis,
                            "summary.locked": 1,
                        })

                    if args.replace_poster and title.episode_poster:
                        if title.autocrop:
                            title.episode_poster = autocrop(
                                title.episode_poster, service.session)

                        if check_url_exist(title.episode_poster, service.session):
                            show.season(title.season).episode(
                                title.episode).uploadPoster(url=title.episode_poster)
                        elif Path(title.episode_poster).exists():
                            show.season(title.season).episode(
                                title.episode).uploadPoster(filepath=title.episode_poster)
                            os.remove(title.episode_poster)
            else:
                if plex:
                    movie = plex.plex_find_lib(
                        'movie', args.plex_title, title.name)
                    if title.synopsis:
                        movie.edit(**{
                            "summary.value": title.synopsis,
                            "summary.locked": 1,
                        })
                    if title.content_rating:
                        movie.edit(**{
                            "contentRating.value": title.content_rating,
                            "contentRating.locked": 1,
                        })
                    if args.replace_poster and check_url_exist(title.poster, service.session):
                        movie.uploadPoster(url=title.poster)

    # url = args.url
    # title = args.title
    # input_summary = args.input_summary
    # replace = args.replace
    # replace_poster = args.replace_poster
    # print_only = args.print_only
    # download_poster = args.download_poster

    # if title:
    #     title = title.strip()


    # if args.season_index:
    #     season_index = int(args.season_index)
    # else:
    #     season_index = 1
    # plex = ''
    # if not print_only:
    #     plex = connect_plex()
    # if 'netflix' in url:
    #     netflix = Netflix(args)
    #     netflix.main()
    # elif 'hbogoasia' in url:
    #     hbogoasia = HBOGOAsia(args)
    #     hbogoasia.main()
    # elif 'disney' in url:
    #     disneyplus = DisneyPlus(args)
    #     disneyplus.main()
    # elif 'amazon' in url or 'primevideo' in url:
    #     amazon = Amazon(args)
    #     amazon.main()
    # elif 'tv.apple.com' in url:
    #     appletv = AppleTV(args)
    #     appletv.main()
    # elif 'itunes.apple.com' in url:
    #     itunes = iTunes(args)
    #     itunes.main()
    # elif 'play.google.com' in url:
    #     googleplay = GooglePlay(args)
    #     googleplay.main()
    # elif 'iq.com' in url:
    #     iqiyi = IQIYI(args)
    #     iqiyi.main()
    # elif 'video.friday' in url:
    #     friday = Friday(args)
    #     friday.main()
    # elif 'myvideo' in url:
    #     myvideo = MyVideo(args)
    #     myvideo.main()
    # elif 'kktv' in url:
    #     kktv = KKTV(args)
    #     kktv.main()
    # elif 'hamivideo' in url:
    #     hamivideo = HamiVideo(args)
    #     hamivideo.main()
    # elif 'mod.cht.com.tw' in url:
    #     mod.get_metadata(get_dynamic_html(url), plex,
    #                      title, print_only, season_index)
    # elif 'japan.videoland' in url:
    #     videoland.get_metadata(get_dynamic_html(
    #         url), plex, title, replace_poster, print_only, season_index)
    # elif 'baidu' in url:
    #     baidu.get_metadata(get_dynamic_html(
    #         url), plex, title, print_only, season_index)
    # elif 'thetvdb' in url:
    #     thetvdb.get_metadata(get_dynamic_html(
    #         url), plex, title, replace_poster, print_only, season_index)
    # elif 'chiblog' in url:
    #     chiblog.get_metadata(get_dynamic_html(
    #         url), plex, title, print_only, season_index)
    # elif 'pixnet.net' in url:
    #     pixnet.get_metadata(get_static_html(
    #         url), plex, title, print_only, season_index)
    # elif 'tpcatv' in url:
    #     tpcatv.get_metadata(get_dynamic_html(
    #         url), plex, title, print_only, season_index)
    # elif 'mactv' in url:
    #     mactv.get_metadata(get_dynamic_html(
    #         url), plex, title, print_only, season_index)
    # elif replace and title:
    #     custom.replace_episode(plex, title,
    #                            args.replace, input_summary)
    # else:
    #     print("目前只支持從Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等取得電影、影集資訊")
if __name__ == "__main__":
    main()
