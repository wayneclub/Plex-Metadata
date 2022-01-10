"""
This module is to get Netflix, HBOGo, Friday, iTune, etc metadata and automatically apply to Plex.
https://python-plexapi.readthedocs.io/en/latest/index.html
"""

import argparse
import logging
from datetime import datetime
import os
from services import amazon, baidu, chiblog, custom, friday, myvideo, kktv, mactv, mod, pixnet, thetvdb, tpcatv, videoland
from services.netflix import Netflix
from services.itunes import iTunes
from services.appletv import AppleTV
from services.hbogoasia import HBOGOAsia
from services.disneyplus import DisneyPlus
from common.utils import connect_plex, get_static_html, get_dynamic_html

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='取得Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等電影、影集資訊')

    parser.add_argument(
        'url', help='Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等介紹網址')

    parser.add_argument('-t', '--title', dest='title', help='影集名稱')

    parser.add_argument('-i', '--input_summary',
                        dest='input_summary', help='劇情檔案')

    parser.add_argument('-r', '--replace', dest='replace',
                        nargs='?', const=True, help='取代標題')

    parser.add_argument('-rp', '--replace_poster', dest='replace_poster',
                        nargs='?', const=True, help='取代標題')

    parser.add_argument('-p', '--print_only', dest='print_only',
                        nargs='?', const=True, help='只印出不要更新')

    parser.add_argument('-s', '--season_index',
                        dest='season_index', type=int, help='季')

    parser.add_argument('-region', '--region', dest='region', help='詮釋資料地區')

    parser.add_argument('-d', '--download_poster', dest='download_poster',
                        nargs='?', const=True, help='下載海報')

    parser.add_argument('-o',
                        '--output',
                        dest='output',
                        help='下載路徑')
    parser.add_argument(
        '-debug',
        '--debug',
        action='store_true',
        help="enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(
                    f"Subtitle-Downloader_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            format='%(message)s',
            level=logging.INFO,
        )

    url = args.url
    title = args.title
    input_summary = args.input_summary
    replace = args.replace
    replace_poster = args.replace_poster
    print_only = args.print_only
    download_poster = args.download_poster

    if title:
        title = title.strip()

    if args.season_index:
        season_index = int(args.season_index)
    else:
        season_index = 1

    output = args.output
    if not output:
        output = os.getcwd()

    plex = ''
    if not print_only:
        plex = connect_plex()

    if 'netflix' in url:
        netflix = Netflix(args)
        netflix.main()
        # change_poster_only = False
        # if not re.search(r'\/(sg-zh|hk|tw|mo)\/title', url):
        #     change_poster_only = True
        # if 'sg-zh' in url:
        #     netflix.get_metadata(get_static_html(url), plex,
        #                          title, replace_poster, print_only, season_index, change_poster_only, translate=True)
        # else:
        #     netflix.get_metadata(get_static_html(url), plex,
        #                          title, replace_poster, print_only, season_index, change_poster_only)
    elif 'hbogoasia' in url:
        hbogoasia = HBOGOAsia(args)
        hbogoasia.main()
        # hbogo.get_metadata(get_dynamic_html(
        #     url), plex, title, replace_poster, print_only)
    elif 'disney' in url:
        # disney.get_metadata(url, plex, title, args.language, replace_poster,
        #                     print_only, download_poster, output)
        disneyplus = DisneyPlus(args)
        disneyplus.main()
    elif 'amazon' in url:
        amazon.get_metadata(get_static_html(url), plex,
                            title, replace_poster, print_only)
    elif 'tv.apple.com' in url:
        appletv = AppleTV(args)
        appletv.main()
    elif 'itunes.apple.com' in url:
        itunes = iTunes(args)
        itunes.main()
        # itunes.get_metadata(get_dynamic_html(url), plex, title, print_only)
    elif 'video.friday' in url:
        friday.get_metadata(get_dynamic_html(
            url), plex, title, replace_poster, print_only)
    elif 'myvideo' in url:
        myvideo.get_metadata(get_static_html(
            url), plex, title, replace_poster, print_only)
    elif 'kktv' in url:
        kktv.get_metadata(get_static_html(
            url), plex, title, replace_poster, print_only)
    elif 'mod.cht.com.tw' in url:
        mod.get_metadata(get_dynamic_html(url), plex,
                         title, print_only, season_index)
    elif 'japan.videoland' in url:
        videoland.get_metadata(get_dynamic_html(
            url), plex, title, replace_poster, print_only, season_index)
    elif 'baidu' in url:
        baidu.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_index)
    elif 'thetvdb' in url:
        thetvdb.get_metadata(get_dynamic_html(
            url), plex, title, replace_poster, print_only, season_index)
    elif 'chiblog' in url:
        chiblog.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_index)
    elif 'candybear98.pixnet.net' in url:
        pixnet.get_metadata(get_static_html(
            url), plex, title, print_only, season_index)
    elif 'tpcatv' in url:
        tpcatv.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_index)
    elif 'mactv' in url:
        mactv.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_index)
    elif replace and title:
        custom.replace_episode(plex, title,
                               args.replace, input_summary)
    else:
        print("目前只支持從Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等取得電影、影集資訊")
