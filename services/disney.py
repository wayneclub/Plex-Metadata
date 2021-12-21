import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from common.utils import import_credential, get_dynamic_html, plex_find_lib, text_format


def login():
    credential = import_credential()
    email = credential['disney_plus']['email']
    password = credential['disney_plus']['password']

    driver = get_dynamic_html("https://www.disneyplus.com/login", False)
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

            if not print_only:
                show = plex_find_lib(plex, 'show', plex_title, title)

            if '/series' in url:
                if WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-testid, 'season')]"))):
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

                for season_index, season in enumerate(season_list, start=1):

                    for episode_index, episode in enumerate(season, start=1):
                        time.sleep(1)
