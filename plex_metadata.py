"""
This module is to get Netflix, HBOGo, Friday, iTune, etc metadata and automatically apply to Plex.
https://python-plexapi.readthedocs.io/en/latest/index.html
"""

import argparse
import re
from services import appletv, baidu, chiblog, custom, disney, friday, hbogo, itunes, mactv, mod, netflix, pixnet, thetvdb, tpcatv, videoland
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

    parser.add_argument('-s', '--season_num',
                        dest='season_num', type=int, help='季')

    args = parser.parse_args()

    url = args.url
    title = args.title
    input_summary = args.input_summary
    replace = args.replace
    replace_poster = args.replace_poster
    print_only = args.print_only

    if title:
        title = title.strip()

    if args.season_num:
        season_num = int(args.season_num)
    else:
        season_num = 1

    plex = ''
    if not print_only:
        plex = connect_plex()

    if 'netflix' in url:
        change_poster_only = False
        if not re.search(r'\/(sg-zh|hk|tw|mo)\/title', url):
            change_poster_only = True
        if 'sg-zh' in url:
            netflix.get_metadata(get_static_html(url), plex,
                                 title, replace_poster, print_only, season_num, change_poster_only, translate=True)
        else:
            netflix.get_metadata(get_static_html(url), plex,
                                 title, replace_poster, print_only, season_num, change_poster_only)
    elif 'hbogo' in url:
        hbogo.get_metadata(get_dynamic_html(
            url), plex, title, replace_poster, print_only)
    elif 'disney' in url:
        disney.get_metadata(disney.login(), url, plex,
                            title, replace_poster, print_only)
    elif 'tv.apple.com' in url:
        appletv.get_metadata(get_dynamic_html(
            url, False), plex, title, replace_poster, print_only)
    elif 'itunes' in url:
        itunes.get_metadata(url, plex, title, print_only)
    elif 'video.friday' in url:
        friday.get_metadata(get_dynamic_html(
            url), plex, title, print_only)
    elif 'mod.cht.com.tw' in url:
        mod.get_metadata(get_dynamic_html(url), plex,
                         title, print_only, season_num)
    elif 'japan.videoland' in url:
        videoland.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_num)
    elif 'baidu' in url:
        baidu.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_num)
    elif 'thetvdb' in url:
        thetvdb.get_metadata(get_dynamic_html(
            url), plex, title, replace_poster, print_only, season_num)
    elif 'chiblog' in url:
        chiblog.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_num)
    elif 'candybear98.pixnet.net' in url:
        pixnet.get_metadata(get_static_html(
            url), plex, title, print_only, season_num)
    elif 'tpcatv' in url:
        tpcatv.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_num)
    elif 'mactv' in url:
        mactv.get_metadata(get_dynamic_html(
            url), plex, title, print_only, season_num)
    elif replace and title:
        custom.replace_episode(plex, title,
                               args.replace, input_summary)
    else:
        print('目前只支持從Netflix、Disney、HBOGO、Apple TV、iTunes、Friday等取得電影、影集資訊')
