"""
This module is for common tool.
"""
import os
import json
import platform
import re
import time
import shutil
from urllib import request
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from plexapi.server import PlexServer
import multiprocessing
import wget
from PIL import Image
from io import BytesIO


def get_static_html(url, json_request=False):
    """Get static html"""
    try:
        headers = {
            'User-Agent': 'User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        }
        req = request.Request(url, headers=headers)
        response = request.urlopen(req)

        if json_request:
            try:
                return json.loads(response.read())
            except json.decoder.JSONDecodeError:
                print("String could not be converted to JSON")
        else:
            return BeautifulSoup(response.read(), 'lxml')

    except HTTPError as exception:
        print(f"HTTPError: {exception.code}")
    except URLError as exception:
        print(f"URLError: {(exception.reason)}")


def get_dynamic_html(url, headless=True):
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
    prefs = {'intl.accept_languages': 'zh,zh_TW',
             'credentials_enable_service': False, 'profile.password_manager_enabled': False}
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    if platform.system() == 'Windows':
        driver = webdriver.Chrome(ChromeDriverManager(
            log_level=0).install(), options=options)
    else:
        driver = webdriver.Chrome('chromedriver', options=options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
    driver.delete_all_cookies()
    driver.get(url)
    driver.set_page_load_timeout(60)
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


def import_credential():
    if os.path.basename(os.getcwd()) == 'Plex-Metadata':
        credential_path = os.path.join(
            os.getcwd(), 'config/my_credential.json')
    else:
        credential_path = os.path.join(
            os.getcwd(), 'Plex-Metadata/config/my_credential.json')

    if not os.path.exists(credential_path):
        credential_path = credential_path.replace(
            'my_credential.json', 'credential.json')

    try:
        with open(credential_path) as json_file:
            return json.load(json_file)
    except json.decoder.JSONDecodeError:
        print("String could not be converted to JSON")


def connect_plex():
    credential = import_credential()
    return PlexServer(credential['plex']['baseurl'], credential['plex']['token'])


def plex_find_lib(plex, lib_type, plex_title="", title=""):
    if plex_title:
        lib = plex.library.search(title=plex_title, libtype=lib_type)
    else:
        lib = plex.library.search(title=title, libtype=lib_type)

    if not plex_title and not lib:
        correct_title = input("請輸入正確標題：")
        lib = plex.library.search(title=correct_title, libtype=lib_type)
        if not lib:
            print(f"plex找不到{title}，請附上正確標題")
            exit(1)
        else:
            lib = lib[0]
    elif len(lib) > 1:
        print(lib)
        correct_index = int(input("請選擇要改的編號："))
        lib = lib[correct_index]
    else:
        lib = lib[0]

    return lib


def text_format(text):
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
        text = text.replace('飾）', ' 飾）')
        text = re.sub(r'([\u4E00-\u9FFF]) ', '\\1，', text)
        text = re.sub(r' ([\u4E00-\u9FFF])', '，\\1', text)
        text = text.replace('，飾）', ' 飾）')
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
        if len(text) > 100:
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
    pool = multiprocessing.Pool(
        cpus if cpus < max_pool_size else max_pool_size)
    for url in urls:
        pool.apply_async(download_file, args=(
            url, os.path.join(folder_path, f'{os.path.basename(url)}.png')))
    pool.close()
    pool.join()

    # print("\n將海報封裝打包：\n---------------------------------------------------------------")
    # print(f'{os.path.basename(folder_path)}.zip')
    # shutil.make_archive(os.path.basename(folder_path), 'zip', folder_path)


def download_file(url, output):
    wget.download(url, out=output)


def compress_image(url):
    image_path = f'{os.path.join(os.getcwd(), os.path.basename(url))}.webp'
    image = Image.open(BytesIO(request.urlopen(url).read()))
    image.save(image_path, 'webp', optimize=True, quality=100)
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
