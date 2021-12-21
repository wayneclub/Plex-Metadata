import re
import time
import json
import os
from urllib import request
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.utils import save_file
from common.utils import import_credential, get_dynamic_html, plex_find_lib, text_format, save_html, download_posters


def login():
    credential = import_credential()
    email = credential['disney_plus']['email']
    password = credential['disney_plus']['password']

    driver = get_dynamic_html("https://www.disneyplus.com/login")
    print("登入Disney+...")

    email_input = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.ID, 'email')))
    email_input.send_keys(email)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[@data-testid='login-continue-button']"))).click()
    time.sleep(1)

    password_input = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.ID, 'password')))
    cookie_button = driver.find_elements(
        By.XPATH, "//button[@id='onetrust-accept-btn-handler']")
    if cookie_button:
        cookie_button[0].click()
    password_input.send_keys(password)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[@data-testid='password-continue-login']"))).click()

    time.sleep(3)

    driver.refresh()

    time.sleep(1)

    username = ''
    if '/select-profile' in driver.current_url:
        user = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@data-testid='profile-avatar-0']")))
        username = user.text
        user.click()
    else:
        driver.get("https://www.disneyplus.com/select-profile")
        user = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@data-testid='profile-avatar-0']")))
        username = user.text
        user.click()

    time.sleep(3)

    if '/home' in driver.current_url:
        print(
            f"登入成功...\n歡迎 {username} 使用Disney+\n---------------------------------------------------------------")
    else:
        print(driver.current_url)

    return driver


def get_metadata(driver, url, plex, plex_title="", replace_poster="", print_only=False):
    driver.get(url)

    if WebDriverWait(driver, 10).until(EC.url_to_be(url)):

        if WebDriverWait(driver, 10, 0.5).until(EC.title_contains('觀看')):
            title = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//h1'))).text.strip()

            print(f"{title}")

            if not print_only:
                show = plex_find_lib(plex, 'show', plex_title, title)

            if '/series' in url:
                if WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//button[contains(@data-testid, 'season')]"))):
                    season_buttons = driver.find_elements(
                        By.XPATH, "//button[contains(@data-testid, 'season')]")

                    season_start = 0
                    season_end = len(season_buttons)

                travel_button = driver.find_elements(
                    By.XPATH, "//button[@data-testid='modal-primary-button']")
                if travel_button:
                    travel_button[0].click()

                season_list = []
                for season_button in season_buttons[season_start:season_end]:
                    total_episode = season_button.get_attribute(
                        'aria-label').replace('。', '').replace('，', '：')
                    print(total_episode)
                    episode_num = int(
                        re.sub(r'第\d+季：共(\d+)集', '\\1', total_episode))
                    time.sleep(1)
                    if season_button.is_enabled():
                        season_button.click()
                        time.sleep(1)
                    episode_list = driver.find_elements(
                        By.XPATH, "//div[@data-program-type='episode']")

                    while len(episode_list) != episode_num:
                        next_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(
                            (By.XPATH, "//button[@data-testid='arrow-right']")))

                        if int(next_button.get_attribute('tabindex')) == 0:
                            ActionChains(driver).move_to_element(
                                next_button).click(next_button).perform()

                        episode_list = driver.find_elements(
                            By.XPATH, "//div[@data-program-type='episode']")

                    web_content = BeautifulSoup(driver.page_source, 'lxml')
                    episode_list = web_content.find_all(
                        'div', {'data-program-type': 'episode'})
                    season_list.append(episode_list)

                posters = set()
                for season_index, season in enumerate(season_list, start=1):
                    episodes = []
                    for episode_index, episode_content in enumerate(season, start=1):
                        time.sleep(1)
                        episode_id = episode_content.find(
                            'a')['data-gv2elementvalue']

                        episode_url = f'https://www.disneyplus.com/zh-hant/video/{episode_id}'
                        driver.get(episode_url)

                        data_url = get_json_data(driver, episode_id)
                        episode, images = parse_json(data_url)
                        episodes.append(episode)
                        posters = set.union(posters, images)

                    for episode_index, episode in enumerate(episodes, start=1):
                        if season_index == 1 and episode_index == 1:
                            print(f"\n{episode['show_synopsis']}")
                            print(episode['show_poster'])
                            if not print_only:
                                show.edit(**{
                                    "summary.value": episode['show_synopsis'],
                                    "summary.locked": 1,
                                })
                                if replace_poster:
                                    show.uploadPoster(
                                        url=episode['show_poster'])

                        if episode_index == 1:
                            print(
                                f"\n第 {season_index} 季\n{episode['season_synopsis']}")
                            if season_index and not print_only:
                                show.season(season_index).edit(**{
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
                                show.season(season_index).episode(
                                    episode_index).uploadPoster(url=episode['poster'])
                driver.quit()
                download_posters(
                    list(posters), os.path.join(os.getcwd(), title))


def get_json_data(driver, episode_id):
    data = ''
    delay = 0
    logs = []
    while not data:
        time.sleep(2)
        logs += driver.execute_script(
            "return window.performance.getEntries();")

        data = next((log['name'] for log in logs
                     if re.search(f"https://disney.content.edge.bamgrid.com/svc/content/DmcVideo/.+{episode_id}", log['name'])), None)
        # print(m3u_file)
        delay += 1

        if delay > 60:
            print("找不到data，請重新執行")
            exit(1)

    return data


def parse_json(data_url):
    try:
        with request.urlopen(data_url) as url:
            data = json.loads(url.read().decode())
            drama = data['data']['DmcVideo']['video']
            if drama:
                episode = dict()
                for text in drama['texts']:
                    if text['sourceEntity'] == 'program' and text['type'] == 'full':
                        if text['field'] == 'title':
                            episode['title'] = text['content']
                        if text['field'] == 'description':
                            episode['synopsis'] = text_format(text['content'])
                    if text['type'] == 'medium':
                        if text['sourceEntity'] == 'series':
                            episode['show_synopsis'] = text_format(
                                text['content'])
                        if text['sourceEntity'] == 'season':
                            episode['season_synopsis'] = text_format(
                                text['content'])

                images = set()
                for image in drama['images']:
                    if image['sourceEntity'] == 'series' and image['purpose'] == 'tile' and image['aspectRatio'] == 0.75:
                        episode['show_poster'] = image['url']
                    if image['sourceEntity'] == 'program' and image['purpose'] == 'thumbnail':
                        episode['poster'] = image['url']
                    images.add(image['url'])

                return episode, images

    except json.decoder.JSONDecodeError:
        print("String could not be converted to JSON")
