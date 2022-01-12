import re
from common.utils import plex_find_lib, text_format
from common.dictionary import translate_text, convert_chinese_number


def replace_episode(plex, plex_title, language="", input_summary=""):
    show = plex_find_lib(plex, 'show', plex_title)

    if input_summary:
        with open(input_summary, 'r') as file:
            summary = file.readlines()

    print(f"\n{show.title}")
    for season in show:
        print(f"\n{season.title}")
        for index, episode in enumerate(season, start=1):
            episode_title = episode.title
            if re.search(r'[\u4E00-\u9FFF]', episode_title):
                if re.search(r'剧([0-9]+)集', episode_title):
                    episode_title = re.sub(
                        r'剧([0-9]+)集', '第 \\1 集', episode_title)
                if re.search(r'第([0-9]+)集', episode_title):
                    episode_title = re.sub(
                        r'第([0-9]+)集', '第 \\1 集', episode_title)
                if re.search(r'^第.+集$', episode_title):
                    episode_number = int(convert_chinese_number(
                        episode_title.replace('第', '').replace('集', '').strip()))
                    episode_title = f'第 {episode_number} 集'
                if language == 'cn':
                    episode_title = text_format(translate_text(episode_title))
            else:
                episode_title = f'第 {index} 集'
            episode_title = episode_title.replace('。', '')
            episode_title = re.sub(r'第.+[話|集] ', '', episode_title)

            episode_summary = episode.summary

            if input_summary:
                # episode_title = text_format(summary[index-1].split('：')[0])
                # episode_summary = text_format(summary[index-1].split('：')[1])
                # episode_title = text_format(summary[index-1])
                episode_summary = text_format(summary[index-1])
            else:
                if language == 'cn':
                    episode_summary = text_format(
                        text_format(translate_text(episode.summary)))
                else:
                    episode_summary = text_format(
                        episode.summary)

            episode_summary = re.sub(r'（[^）]+飾）', '', episode_summary)
            # episode_summary = episode_summary.replace('李淡', '李潭')
            # episode_summary = episode_summary.replace('惠宣', '惠善')
            # episode_summary = episode_summary.replace('秀晶', '秀景')
            # episode_summary = episode_summary.replace('季善宇', '桂善友')
            # episode_summary = episode_summary.replace('睪斬', '甘霖')
            # episode_summary = episode_summary.replace('泰白', '太白')
            print(f"\n{episode_title}\n{episode_summary}")
            episode.edit(**{
                "title.value": episode_title,
                "title.locked": 1,
                "summary.value": episode_summary,
                "summary.locked": 1,
            })
