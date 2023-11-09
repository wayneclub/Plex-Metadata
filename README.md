# Plex-Metadata

[![zh](https://img.shields.io/badge/lang-中文-blue)](https://github.com/wayneclub/Subtitle-Downloader/blob/main/README.zh-Hant.md) [![python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)

**NON-COMMERCIAL USE ONLY**

Plex-Metadata supports auto-fetching metadata and posters from multiple streaming services, such as Amazon, Apple TV+, CatchPlay, Disney+, FridayVideo, Google Play, HamiVideo, HBOGOAsia, iQIYI, KKTV, MyVideo, Netflix, etc.

## DESCRIPTION

Plex-Metadata is a command-line program to download metadata and posters from the most popular streaming platform. It requires **[Python 3.10+](https://www.python.org/downloads/)**, and **[NodeJS](https://nodejs.org/en/download)**. It should work on Linux, on Windows, or macOS. This project is only for personal research and language learning.

## INSTALLATION

- Linux, macOS:

```bash
pip install -r requriements.txt
```

- Windows: Execute `install_requirements.bat`

## Service Requirements

| Name | Authentication |
| ---- | -------------- |
| Netflix | Cookies |

### Get Cookies

1. Install Chrome plugin: [get-cookiestxt-locally](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Login to the streaming service, and use the plugin to download cookies.txt (Don't modify anything even the file name)
3. Put cookie.txt into `Plex-Metadata/cookies`

## USAGE

### Local

1. Depending on the download platform and modify `Plex-Metadata/user_config.toml`

    ```toml
    [metadata]
    default-language = 'zh-Hant' # en/zh-Hant

    [metadata.Amazon]
    locale = 'zh_TW' # en_US, zh_TW

    [metadata.AppleTVPlus]
    locale = 'zh-TW' # en-US, zh-TW

    [metadata.DisneyPlus]
    region = 'TW' # US, TW, HK

    [metadata.GooglePlay]
    region = 'TW'    # US, TW
    locale = 'zh-TW' # en-US, zh-TW

    [metadata.Netflix]
    region = 'tw' # us, tw, hk
    ```

2. Follow each platform's requirements and put cookies.txt into `Plex-Metadata/cookies`
3. Execute the program with the command line

    ```bash
    python plex_metadata.py URL [OPTIONS]
    ```

## OPTIONS

```text
  -h, --help                    show this help message and exit

  -s, --season                  download season [0-9]

  -e, --episode                 download episode [0-9]

  -t, --title                   plex media title

  -r, --replace                 replace metadata

  -rp, --replace-poster         replace poster

  -dl, --download-poster        download posters

  -locale, --locale             interface language

  -p, --proxy                   proxy

  -d, --debug                   enable debug logging

  -v, --version                 app's version
```

## More Examples

- Print all seasons and all episodes' metadata

```bash
python plex_metadata.py URL
```

- Replace all seasons and all episodes' metadata on Plex

```bash
python plex_metadata.py URL -r
```

- Replace all seasons and all episodes' metadata on Plex with the title X

```bash
python plex_metadata.py URL -r -t "X"
```

- Replace season 1 episode 1's metadata on Plex

```bash
python plex_metadata.py URL -s 1 -e 1 -r
```

- Replace all seasons and all episodes' posters on Plex

```bash
python plex_metadata.py URL -rp
```

- Download all seasons and all episodes' posters

```bash
python plex_metadata.py URL -dl
```

## FAQ

- Any issue during downloading metadata and posters, upload the screenshot and log file (Please provide title, platform, and region).

## Support & Contributions

- Please ⭐️ this repository if this project helped you!
- Contributions of any kind are welcome!

 <a href="https://www.buymeacoffee.com/wayneclub" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/black_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
