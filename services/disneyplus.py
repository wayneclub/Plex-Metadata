import os
import math
import re
import logging
from common.utils import compress_image, get_static_html, plex_find_lib, save_html, text_format, download_images
from services.service import Service


class DisneyPlus(Service):
    def __init__(self, args):
        super().__init__(args)
        self.logger = logging.getLogger(__name__)

        if args.region:
            self.region = args.region.upper()
        else:
            self.region = 'TW'

        self.output = args.output
        if not self.output:
            self.output = os.getcwd()

        self.download_poster = args.download_poster

    def get_metadata(self):

        posters = set()
        if '/series' in self.url:
            if self.region and 'HK' in self.region:
                series_url = f'https://disney.content.edge.bamgrid.com/svc/content/DmcSeriesBundle/version/5.1/region/{self.region}/audience/false/maturity/1850/language/zh-HK/encodedSeriesId/{os.path.basename(self.url)}'
            else:
                series_url = f'https://disney.content.edge.bamgrid.com/svc/content/DmcSeriesBundle/version/5.1/region/{self.region}/audience/false/maturity/1850/language/zh-Hant/encodedSeriesId/{os.path.basename(self.url)}'

            data = get_static_html(series_url, True)['data']['DmcSeriesBundle']
            title = data['series']['text']['title']['full']['series']['default']['content']
            show_synopsis = data['series']['text']['description']['medium']['series']['default']['content']

            if 'background_details' in data['series']['image']:
                show_background = data['series']['image']['background_details']['1.78']['series']['default']['url']
            elif 'background' in data['series']['image']:
                show_background = data['series']['image']['background']['1.78']['series']['default']['url']

            print(f"{title}\n{show_synopsis}\n{show_background}")

            if not self.print_only:
                show = plex_find_lib(self.plex, 'show', self.plex_title, title)
                show.edit(**{
                    "summary.value": show_synopsis,
                    "summary.locked": 1
                })
                if self.replace_poster:
                    show_background_file = compress_image(show_background)
                    show.uploadArt(filepath=show_background_file)
                    if os.path.exists(show_background_file):
                        os.remove(show_background_file)

            backgrounds = set()
            season_num = len(data['seasons']['seasons'])
            for season in data['seasons']['seasons']:
                season_index = season['seasonSequenceNumber']
                episode_list = self.check_episodes(season, series_url)
                for episode_id in episode_list:
                    episode_url = re.sub(r'(.+)DmcSeriesBundle(.+)encodedSeriesId.+',
                                         '\\1DmcVideo\\2contentId/', series_url) + episode_id
                    # print(episode_url)
                    episode_data = get_static_html(
                        episode_url, True)['data']['DmcVideo']['video']
                    episode, background_list, poster_list = self.parse_json(
                        episode_data)

                    episode_index = episode['index']
                    backgrounds = set.union(backgrounds, background_list)
                    posters = set.union(posters, poster_list)

                    if season_index == 1 and episode_index == 1:
                        print(episode['show_poster'])
                        if not self.print_only and self.replace_poster:
                            show_poster_file = compress_image(
                                episode['show_poster'])
                            show.uploadPoster(filepath=show_poster_file)
                            if season_num == 1:
                                show.season(season_index).uploadPoster(
                                    filepath=show_poster_file)
                            if os.path.exists(show_poster_file):
                                os.remove(show_poster_file)

                    if episode_index == 1:
                        print(
                            f"\n第 {season_index} 季\n{episode['season_synopsis']}")
                        if season_index and not self.print_only:
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

                    if not self.print_only and episode_index:
                        show.season(season_index).episode(episode_index).edit(**{
                            "title.value": episode['title'],
                            "title.locked": 1,
                            "summary.value": episode['synopsis'],
                            "summary.locked": 1,
                        })

                        if self.replace_poster:

                            episode_poster_file = compress_image(
                                episode['poster'])
                            show.season(season_index).episode(
                                episode_index).uploadPoster(filepath=episode_poster_file)
                            if os.path.exists(episode_poster_file):
                                os.remove(episode_poster_file)

            print()
            backgrounds.remove(show_background)
            for season_index, poster in enumerate(list(backgrounds)[1:], start=1):
                print(poster)
                if self.replace_poster and season_index <= season_num:
                    season_background_file = compress_image(poster)
                    show.season(season_index).uploadArt(
                        filepath=season_background_file)
                    if os.path.exists(season_background_file):
                        os.remove(season_background_file)
        elif '/movies' in self.url:
            if self.region and 'HK' in self.region:
                movie_url = f'https://disney.content.edge.bamgrid.com/svc/content/DmcVideoBundle/version/5.1/region/{self.region}/audience/false/maturity/1850/language/zh-HK/encodedFamilyId/{os.path.basename(self.url)}'
            else:
                movie_url = f'https://disney.content.edge.bamgrid.com/svc/content/DmcVideoBundle/version/5.1/region/{self.region}/audience/false/maturity/1850/language/zh-Hant/encodedFamilyId/{os.path.basename(self.url)}'
            print(movie_url)
            res = self.session.get(movie_url)

            if res.ok:
                data = res.json()['data']['DmcVideoBundle']['video']
                # print(data)
                movie_id = data['contentId']
                title = data['text']['title']['full']['program']['default']['content'].strip(
                )
                movie_synopsis = data['text']['description']['medium']['program']['default']['content']

                if 'background_details' in data['image']:
                    movie_background = data['image']['background_details']['1.78']['program']['default']['url']
                elif 'background' in data['image']:
                    movie_background = data['image']['background']['1.78']['program']['default']['url']

                if 'tile' in data['image']:
                    movie_poster = data['image']['tile']['0.71']['program']['default']['url']

                print(
                    f"{title}\n{movie_synopsis}\n{movie_background}\n{movie_poster}")
                video_url = re.sub(r'(.+)DmcVideoBundle(.+)encodedFamilyId.+',
                                   '\\1DmcVideo\\2contentId/', movie_url) + movie_id
                video_data = get_static_html(video_url, True)[
                    'data']['DmcVideo']['video']['image']
                for image_key in video_data.keys():
                    if not 'title' in image_key:
                        print(image_key)
                        if '1.78' in video_data[image_key]:
                            posters.add(video_data[image_key]['1.78']
                                        ['program']['default']['url'])
                        if '0.71' in video_data[image_key]:
                            posters.add(video_data[image_key]['0.71']
                                        ['program']['default']['url'])

                if not self.print_only:
                    movie = plex_find_lib(self.plex, 'movie',
                                          self.plex_title, title)
                    movie.edit(**{
                        "summary.value": movie_synopsis,
                        "summary.locked": 1
                    })
                    if self.replace_poster:
                        movie_poster_file = compress_image(movie_poster)
                        movie.uploadPoster(filepath=movie_poster_file)
                        if os.path.exists(movie_poster_file):
                            os.remove(movie_poster_file)

                        movie_background_file = compress_image(
                            movie_background)
                        movie.uploadArt(filepath=movie_background_file)
                        if os.path.exists(movie_background_file):
                            os.remove(movie_background_file)

        print()
        print('\n'.join(posters))
        if self.download_poster:
            download_images(posters, os.path.join(self.output, title))

    def check_episodes(self, season, series_url):
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

    def parse_json(self, data):
        episode = dict()
        episode['index'] = data['episodeSequenceNumber']
        episode['title'] = data['text']['title']['full']['program']['default']['content']
        episode['synopsis'] = text_format(
            data['text']['description']['full']['program']['default']['content'])
        episode['season_synopsis'] = text_format(
            data['text']['description']['medium']['season']['default']['content'])

        episode['show_poster'] = data['image']['tile']['0.71']['series']['default']['url']
        episode['poster'] = data['image']['thumbnail']['1.78']['program']['default']['url']
        images = set()
        posters = set()
        for image_key in data['image'].keys():
            if not 'title' in image_key:
                if not 'tile' in image_key and '1.78' in data['image'][image_key] and 'series' in data['image'][image_key]['1.78']:
                    # print(image_key)
                    images.add(data['image'][image_key]['1.78']
                               ['series']['default']['url'])

                if '1.78' in data['image'][image_key]:
                    if 'series' in data['image'][image_key]['1.78']:
                        posters.add(data['image'][image_key]['1.78']
                                    ['series']['default']['url'])
                    if 'program' in data['image'][image_key]['1.78']:
                        posters.add(data['image'][image_key]['1.78']
                                    ['program']['default']['url'])
                if '0.71' in data['image'][image_key]:
                    posters.add(data['image'][image_key]['0.71']
                                ['series']['default']['url'])

        return episode, images, posters

    def main(self):
        self.get_metadata()
