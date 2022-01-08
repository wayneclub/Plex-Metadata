import re
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from common.utils import plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", replace_poster="", print_only=False, season_index=1):

    title = driver.find_element(By.XPATH, "//h1[@class='title-chi']").text
    print(f"\n{title}")

    season_regex = re.search(r'.+第([0-9]+)季', title)
    if season_regex:
        season_index = int(season_regex.group(1))

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)

    season_synopsis = text_format(
        driver.find_element(By.XPATH, "//p[contains(@class, 'storyline')]").text)
    print(f"\n{season_synopsis}")

    if not print_only:
        show.season(season_index).edit(**{
            "title.value": f'第 {season_index} 季',
            "title.locked": 1,
            "summary.value": season_synopsis,
            "summary.locked": 1,
        })

    poster_url = driver.find_elements(
        By.XPATH, "//div[@class='photos-content']/img")[-1].get_attribute('src').replace('_M', '')

    if not print_only and replace_poster:
        show.uploadPoster(url=poster_url)

    action = ActionChains(driver)
    for li in driver.find_elements(By.XPATH, "//ul[@class='episode-container']/li"):
        action.move_to_element(li).perform()
        wait = WebDriverWait(driver, 0.5)
        episode_content = wait.until(
            EC.visibility_of_element_located((By.CLASS_NAME, 'episode-content')))

        episode_title = episode_content.find_element(By.CLASS_NAME,
                                                     'epi-title').text
        episode_synopsis = text_format(
            episode_content.find_element(By.CLASS_NAME, 'epi-info').text)

        season_episode_regex = re.search(r'(第([0-9]+)季)*([0-9]+)', li.text)

        if season_episode_regex:
            if season_episode_regex.group(1):
                season_index = int(season_episode_regex.group(2))
                episode_index = int(season_episode_regex.group(3))
            else:
                episode_index = int(li.text)

            if episode_index == 1:
                print(f"\n第 {season_index} 季")

            print(f"\n第 {episode_index} 集：{episode_title}\n{episode_synopsis}")
        else:
            print(f"\n{li.text} {episode_title}\n{episode_synopsis}")

        if not print_only and episode_index:
            if episode_title:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
            else:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": f'第 {episode_index} 集',
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })
    driver.quit()
