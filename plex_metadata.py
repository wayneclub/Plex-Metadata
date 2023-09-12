"""
This module is to get Netflix, HBOGo, Friday, iTune, etc metadata and automatically apply to Plex.

Support doc
https://python-plexapi.readthedocs.io/en/latest/index.html
"""

import argparse
import logging
from datetime import datetime
import os
from services import baidu, chiblog, custom, mactv, mod, pixnet, thetvdb, tpcatv, videoland
from services.netflix import Netflix
from services.itunes import iTunes
from services.appletv import AppleTV
from services.hbogoasia import HBOGOAsia
from services.disneyplus import DisneyPlus
from services.amazon import Amazon
from services.googleplay import GooglePlay
from services.iqiyi import IQIYI
from services.friday import Friday
from services.myvideo import MyVideo
from services.kktv import KKTV
from services.hamivideo import HamiVideo
from configs.config import Config, script_name, __version__
from utils.helper import connect_plex, get_static_html, get_dynamic_html, save_html
from utils.proxy_environ import proxy_env

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

    parser.add_argument('-download', '--download_poster', dest='download_poster',
                        nargs='?', const=True, help='下載海報')

    parser.add_argument('-o',
                        '--output',
                        dest='output',
                        help='下載路徑')
    parser.add_argument('-proxy',
                        '--proxy',
                        dest='proxy',
                        nargs='?',
                        const=True,
                        help="proxy")
    parser.add_argument("--pv",
                        '--private-vpn',
                        action="store",
                        dest="privtvpn",
                        help="add country for privtvpn proxies.",
                        default=0)
    parser.add_argument("-n",
                        '--nord-vpn',
                        action="store",
                        dest="nordvpn",
                        help="add country for nordvpn proxies.",
                        default=0)
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
        version='{script_name} {version}'.format(
            script_name=script_name, version=__version__)
    )

    args = parser.parse_args()
    config = Config()

    if args.debug:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(
                    f"Plex-Metadata_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            format='%(message)s',
            level=logging.INFO,
        )

    config.check_binaries(config.bin())

    ip_info = proxy_env(args).Load()
    args.proxy = ip_info

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
    elif 'hbogoasia' in url:
        hbogoasia = HBOGOAsia(args)
        hbogoasia.main()
    elif 'disney' in url:
        disneyplus = DisneyPlus(args)
        disneyplus.main()
    elif 'amazon' in url or 'primevideo' in url:
        amazon = Amazon(args)
        amazon.main()
    elif 'tv.apple.com' in url:
        appletv = AppleTV(args)
        appletv.main()
    elif 'itunes.apple.com' in url:
        itunes = iTunes(args)
        itunes.main()
    elif 'play.google.com' in url:
        googleplay = GooglePlay(args)
        googleplay.main()
    elif 'iq.com' in url:
        iqiyi = IQIYI(args)
        iqiyi.main()
    elif 'video.friday' in url:
        friday = Friday(args)
        friday.main()
    elif 'myvideo' in url:
        myvideo = MyVideo(args)
        myvideo.main()
    elif 'kktv' in url:
        kktv = KKTV(args)
        kktv.main()
    elif 'hamivideo' in url:
        hamivideo = HamiVideo(args)
        hamivideo.main()
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
    elif 'pixnet.net' in url:
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
