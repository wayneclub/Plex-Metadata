"""
This module is for common tool.
"""
import logging
from operator import itemgetter
import os
import json
import platform
import re
import sys
import time
import shutil
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from natsort import natsorted
import requests
from requests import Session
from selenium import webdriver
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
import multiprocessing
from tqdm import tqdm
import validators
import wget
from PIL import Image
import numpy as np
import cv2
from io import BytesIO
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

from configs.config import config, directories
from utils import Logger


class EpisodesNumbersHandler(object):
    """
    Convert user-input episode range to list of int numbers
    """

    def __init__(self, episodes):
        self.episodes = episodes

    def number_range(self, start: int, end: int):
        if list(range(start, end + 1)) != []:
            return list(range(start, end + 1))

        if list(range(end, start + 1)) != []:
            return list(range(end, start + 1))

        return [start]

    def list_number(self, number: str):
        if number.isdigit():
            return [int(number)]

        if number.strip() == "~" or number.strip() == "":
            return self.number_range(1, 999)

        if "-" in number:
            start, end = number.split("-")
            if start.strip() == "" or end.strip() == "":
                raise ValueError(f"wrong number: {number}")
            return self.number_range(int(start), int(end))

        if "~" in number:
            start, _ = number.split("~")
            if start.strip() == "":
                raise ValueError(f"wrong number: {number}")
            return self.number_range(int(start), 999)

        return

    def sort_numbers(self, numbers):
        sorted_numbers = []
        for number in numbers.split(","):
            sorted_numbers += self.list_number(number.strip())

        return natsorted(list(set(sorted_numbers)))

    def get_episodes(self):
        return (
            self.sort_numbers(
                str(self.episodes).lstrip("0")
            )
            if self.episodes
            else self.sort_numbers("~")
        )


def get_static_html(url, json_request=False):
    """Get static html"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
        res = requests.get(url=url, headers=headers, timeout=5)
        res.encoding = 'utf-8'

        if res.ok:
            if json_request:
                return res.json()
            else:
                return BeautifulSoup(res.text, 'html.parser')

    except HTTPError as exception:
        print(f"HTTPError: {exception.code}")
    except URLError as exception:
        print(f"URLError: {(exception.reason)}")


def get_dynamic_html(url, headless=True):
    """Get html render by js"""
    kill_process()
    # driver_manager = WebdriverAutoUpdate(driver_path)
    # driver_manager.main()

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument("--disable-notifications")
    options.add_argument('window-size=1280,800')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument("--mute-audio")
    options.add_argument('--autoplay-policy=no-user-gesture-required')
    options.add_argument('--lang=zh-TW')
    prefs = {'intl.accept_languages': 'zh,zh_TW',
             'credentials_enable_service': False, 'profile.password_manager_enabled': False}
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    driver = webdriver.Chrome(service=ChromeService(
        ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
    driver.delete_all_cookies()
    driver.get(url)
    driver.set_page_load_timeout(60)
    return driver


def driver_init(headless=True):
    """Get html render by js"""
    kill_process()
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('window-size=1280,800')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument("--mute-audio")
    options.add_argument('--autoplay-policy=no-user-gesture-required')
    options.add_argument('--lang=zh-TW')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    prefs = {'intl.accept_languages': 'zh,zh_TW',
             'credentials_enable_service': False, 'profile.password_manager_enabled': False,
             'profile.default_content_setting_values': {'images': 2, 'plugins': 2, 'popups': 2, 'geolocation': 2, 'notifications': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option(
        'excludeSwitches', ['enable-automation'])
    driver = webdriver.Chrome('chromedriver', options=options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                           "userAgent": Config().get_user_agent()})
    # driver.set_page_load_timeout(3000)
    return driver


def get_network_url(driver, search_url):
    url = ''
    delay = 0
    logs = []
    while not url:
        time.sleep(2)
        logs += driver.execute_script(
            "return window.performance.getEntries();")

        url = next((log['name'] for log in logs
                    if re.search(search_url, log['name'])), None)
        # print(m3u_file)
        delay += 1

        if delay > 60:
            print("找不到data，請重新執行")
            exit(1)
    return url


def connect_plex():
    """Connect Plex"""

    if config.plex['baseurl'] and config.plex['token']:
        return PlexServer(config.plex['baseurl'], config.plex['token'])
    elif config.plex['username'] and config.plex['password'] and config.plex['servername']:
        account = MyPlexAccount(
            config.plex['username'], config.plex['password'])
        return account.resource(config.plex['servername']).connect()


def plex_find_lib(plex, lib_type, plex_title="", title=""):
    if plex_title:
        lib = plex.library.search(title=plex_title, libtype=lib_type)
    else:
        lib = plex.library.search(title=title, libtype=lib_type)
        if not lib:
            title = input("\n請輸入正確標題：")
            lib = plex.library.search(title=title, libtype=lib_type)

    if len(lib) > 1:
        for index, data in enumerate(lib):
            print(f"{index}: {data.title} ({data.year}) [{data.ratingKey}]")

        correct_index = int(input("\n請選擇要改的編號："))
        lib = lib[correct_index]
    elif len(lib) == 1:
        lib = lib[0]
    else:
        print(f"\nplex找不到{title}，請附上正確標題")
        exit(1)

    return lib


def text_format(text, trim=False):
    text = text.strip()
    if re.search(r'[\u4E00-\u9FFF]', text):
        text = text.replace('(', '（')
        text = text.replace(')', '）')
        text = text.replace('!', '！')
        text = text.replace('?', '？')
        text = text.replace(':', '：')
        text = text.replace('。。。', '…')
        text = text.replace('...', '…')
        text = text.replace('．．．', '…')
        text = text.replace('“', '「')
        text = text.replace('”', '」')
        text = text.replace(' （', '（')
        text = text.replace('） ', '）')
        text = text.replace(',', '，')
        text = text.replace(' ，', '，')
        text = text.replace('， ', '，')
        text = text.replace('  ', ' ')
        text = text.replace('  ', ' ')
        text = text.replace('（End）', '')
        text = text.replace('飾演）', '飾）')
        text = text.replace('，飾）', ' 飾）')
        text = text.replace('飾）', ' 飾）')
        text = text.replace('  飾）', ' 飾）')
        # text = re.sub(r'([\u4E00-\u9FFF]) ', '\\1，', text)
        # text = re.sub(r' ([\u4E00-\u9FFF])', '，\\1', text)
        text = text.replace('本季首播.', '')
        text = text.replace('本季首播。', '')
        text = text.replace('劇集首播.', '')
        text = text.replace('劇集首播。', '')
        text = text.replace('本季首集.', '')
        text = text.replace('本季首集。', '')
        text = text.replace('本季第一集.', '')
        text = text.replace('本季第一集。', '')
        text = text.replace('本季最後一集.', '')
        text = text.replace('本季最後一集。', '')
        text = text.replace('本季最後.', '')
        text = text.replace('本季最後。', '')
        text = text.replace('本季最後，', '')
        text = text.replace('本集中,', '')
        text = text.replace('本集中，', '')
        text = '。'.join([tmp.strip() for tmp in text.split('。')])

        if trim and len(text) > 100:
            pos = -1
            if '。' in text[:100]:
                pos = text[:100].rindex('。') + 1
            elif '。' in text[:150]:
                pos = text[:150].rindex('。') + 1
            elif '。' in text[:200]:
                pos = text[:200].rindex('。') + 1
            text = text[:pos]

    return text.strip()


def download_images(urls, folder_path):
    print("\n下載海報：\n---------------------------------------------------------------")
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    cpus = multiprocessing.cpu_count()
    max_pool_size = 8
    pool = multiprocessing.Pool(
        cpus if cpus < max_pool_size else max_pool_size)
    for url in urls:
        pool.apply_async(download_file, args=(
            url, os.path.join(folder_path, f'{os.path.basename(url)}.png')))
    pool.close()
    pool.join()

    print("\n將海報封裝打包：\n---------------------------------------------------------------")
    zipname = os.path.normpath(os.path.basename(folder_path))
    print(f'{zipname}.zip')
    shutil.make_archive(zipname,
                        'zip', os.path.normpath(folder_path))
    if str(os.getcwd()) != str(Path(folder_path).parent.absolute()):
        shutil.move(f'{zipname}.zip',
                    Path(folder_path).parent.absolute())


# def download_file(url, output):
#     wget.download(url, out=output)

def check_url_exist(url: str, session: Session):
    """Validate url exist"""

    if validators.url(url):
        try:
            response = session.head(url, timeout=10)
            if response.ok:
                return True

        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as error:
            logger.error(
                "Failure - Unable to establish connection: %s.", error)
        except Exception as error:
            logger.error("Failure - Unknown error occurred: %s.", error)

    return False


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url, output_path):
    if check_url_exist(url):
        with DownloadProgressBar(unit='B', unit_scale=True,
                                 miniters=1, desc=os.path.basename(output_path)) as t:
            request.urlretrieve(
                url, filename=output_path, reporthook=t.update_to)
    else:
        logger.error("\nFile not found!")
        sys.exit(1)


def multi_thread_download(files):
    cpus = multiprocessing.cpu_count()
    max_pool_size = 8
    pool = multiprocessing.Pool(
        cpus if cpus < max_pool_size else max_pool_size)

    for file in sorted(files, key=itemgetter('name')):
        pool.apply_async(download_file, args=(
            file['url'], file['name']))
    pool.close()
    pool.join()


def compress_image(url):
    image_path = f'{os.path.join(os.getcwd(), os.path.basename(url))}.webp'
    image = Image.open(BytesIO(request.urlopen(url).read()))
    image.save(image_path, 'webp', optimize=True, quality=100)
    return image_path


def autocrop(url: str, session: Session) -> str:
    """Crops any edges below or equal to threshold

    Crops blank image to 1x1.

    Returns cropped image.

    """

    # image = cv2.imread(url)
    # image = Image.open(BytesIO(session.get(url, timeout=10).content))
    image = np.asarray(bytearray(session.get(
        url, timeout=10).content), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    x, y, w, h = cv2.boundingRect(thresh)
    image = image[y:y+h, x:x+w]

    os.makedirs(directories.images, exist_ok=True)
    image_path = Path(directories.images /
                      os.path.basename(url)).with_suffix('.webp')
    cv2.imwrite(str(image_path), image)

    return image_path


def kill_process():
    os.system('killall chromedriver > /dev/null 2>&1')
    os.system('killall Google\\ Chrome > /dev/null 2>&1')
    if platform.system() == 'Darwin':
        os.system(
            "ps -ax | grep 'distnoted agent' | awk '{print $1}' | xargs sudo kill -9")


def save_html(html_source, file='test.html'):
    with open(file, 'w') as writter:
        writter.write(str(html_source))


if __name__:
    logger = Logger.getLogger("helper")
