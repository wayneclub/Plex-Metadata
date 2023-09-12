import re
from selenium.webdriver.common.by import By
from utils.helper import get_dynamic_html, plex_find_lib, text_format


def get_metadata(driver, plex, plex_title="", print_only=False, season_index=1):
    title = driver.find_element(By.XPATH, "//h1").text

    page_element = driver.find_elements(By.XPATH, "//a[@title='Page']")
    if len(page_element) > 0:
        pages = page_element[0].text.split('/')

    print(f"\n{title}")

    if not print_only:
        show = plex_find_lib(plex, 'show', plex_title, title)
        title = show.title

    episode_list = driver.find_element(By.XPATH,
                                       "//*[contains(text(), '分集劇情介紹')]/ancestor::div[contains(@class, 'hjtbox')]/following-sibling::div")

    for episode in episode_list.find_elements(By.XPATH, 'p'):
        episode = episode.text.split('\n')

        if len(episode) == 2:
            episode_regex = re.search(
                r'第([0-9]+)集(-)*(.+)*', episode[0])
            if episode_regex:
                episode_index = int(episode_regex.group(1))

            if re.search(r'[\u4E00-\u9FFF]', show.season(season_index).episode(episode_index).title):
                episode_title = re.sub(
                    r'剧([0-9]+)集', '第 \\1 集', show.season(season_index).episode(episode_index).title)
            else:
                episode_title = f'第 {episode_index} 集'

            if episode_regex and episode_regex.group(3):
                episode_title = text_format(
                    episode_regex.group(3))

            episode_synopsis = text_format(episode[1])

            print(f"\n{episode_title}\n{episode_synopsis}")

            if not print_only and episode_index:
                show.season(season_index).episode(episode_index).edit(**{
                    "title.value": episode_title,
                    "title.locked": 1,
                    "summary.value": episode_synopsis,
                    "summary.locked": 1,
                })

    if not print_only and pages and pages[0] != pages[1]:
        next_page_url = driver.find_element(By.XPATH,
                                            "//a[text()='下一頁']").get_attribute('href')
        get_metadata(get_dynamic_html(next_page_url),
                     plex, title, print_only, season_index)
    else:
        driver.quit()
