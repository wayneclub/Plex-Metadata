#!/usr/bin/python3
# coding: utf-8

"""
This module is to handle subtitles.
"""
import re
import logging
import os
import shutil
import glob
from pathlib import Path
import pysubs2
from chardet import detect
from bs4 import BeautifulSoup
import opencc


def get_encoding_type(source):
    """
    Get file encoding type
    """
    with open(source, 'rb') as source:
        rawdata = source.read()
    return detect(rawdata)['encoding']


def convert_utf8(srcfile):
    """
    Convert file to utf8
    """

    from_codec = get_encoding_type(srcfile)
    try:
        if from_codec.lower() != 'utf-8':
            if from_codec == 'BIG5' or from_codec == 'GBK' or from_codec == 'GB2312' or from_codec == 'Windows-1252' or from_codec == 'ISO-8859-1':
                from_codec = 'CP950'

            with open(srcfile, 'r', encoding=from_codec, errors='replace') as input_src:
                data = input_src.read()
            with open(srcfile, 'w', encoding='UTF-8') as output_src:
                output_src.write(data)

    except UnicodeDecodeError:
        logger.error("Decode Error")
    except UnicodeEncodeError:
        logger.error("Encode Error")


def convert_subtitle(folder_path="", platform=""):
    """
    Convert subtitle to .srt
    """

    if os.path.exists(folder_path):
        vtt_list = glob.glob(os.path.join(folder_path, "*.vtt"))
        dfxp_list = glob.glob(os.path.join(folder_path, "*.dfxp"))

        if vtt_list:
            logger.info(
                "\nConvert .vtt to .srt:\n---------------------------------------------------------------")
            for subtitle in sorted(vtt_list):
                subtitle_name = subtitle.replace(Path(subtitle).suffix, '.srt')
                convert_utf8(subtitle)
                subs = pysubs2.load(subtitle)
                subs = clean_subs(subs)
                if 'zh-Hant' in subtitle_name:
                    subs = format_subtitle(subs)
                subs.save(subtitle_name)
                os.remove(subtitle)
                logger.info(os.path.basename(subtitle_name))

        if dfxp_list:
            logger.info(
                "\nConvert .dfxp to .srt:\n---------------------------------------------------------------")
            for subtitle in sorted(dfxp_list):
                subtitle_name = subtitle.replace(Path(subtitle).suffix, '.srt')
                convert_utf8(subtitle)
                dfxp_to_srt(subtitle, subtitle_name)
                os.remove(subtitle)
                logger.info(os.path.basename(subtitle_name))

        if platform:
            archive_subtitle(path=os.path.normpath(
                folder_path), platform=platform)

    return glob.glob(os.path.join(folder_path, "*.srt"))


def archive_subtitle(path, platform=""):
    """
    Archive subtitles
    """

    logger.info(
        "\nArchive subtitles:\n---------------------------------------------------------------")

    if platform:
        zipname = os.path.basename(f'{path}.WEB-DL.{platform}')
    else:
        zipname = os.path.basename(f'{path}.WEB-DL')

    path = os.path.normpath(path)
    logger.info("%s.zip", zipname)

    shutil.make_archive(zipname, 'zip', path)

    if str(os.getcwd()) != str(Path(path).parent.absolute()):
        exist_zip = os.path.join(
            Path(path).parent.absolute(), f'{os.path.basename(zipname)}.zip')
        if os.path.exists(exist_zip):
            os.remove(exist_zip)
        shutil.move(f'{zipname}.zip', Path(path).parent.absolute())


def ms_to_timestamp(ms: int) -> str:
    """
    Convert ms to 'HH:MM:SS,mmm'
    """
    max_representable_time = 359999999

    if ms < 0:
        ms = 0
    if ms > max_representable_time:
        ms = max_representable_time
    return "%02d:%02d:%02d,%03d" % (pysubs2.time.ms_to_times(ms))


def convert_list_to_subtitle(subs):
    """
    Convert list to subtitle
    """
    text = ''
    for index, sub in enumerate(subs):

        text = text + str(index + 1) + '\n'
        text = text + ms_to_timestamp(sub.start) + \
            ' --> ' + ms_to_timestamp(sub.end) + '\n'
        text = text + \
            sub.text.replace('\\n', '\n').replace('\\N', '\n').strip()
        text = text + '\n\n'

    return pysubs2.ssafile.SSAFile.from_string(text)


def merge_subtitle_fragments(folder_path="", file_name="", display=False, shift_time=[]):
    """
    Merge subtitle fragments
    """

    if os.path.exists(folder_path):
        if display:
            logger.info(
                "\nMerge segments:\n---------------------------------------------------------------")
        subtitles = []
        for segment in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, segment)
            if Path(file_path).suffix in ('.vtt', '.srt'):
                subs = pysubs2.load(file_path)
                if shift_time:
                    offset = next(
                        (seg['offset'] for seg in shift_time if seg['name'] in file_path), '')
                    subs.shift(s=offset)
                subs = clean_subs(subs)
                subtitles += subs
        subs = convert_list_to_subtitle(subtitles)
        subs = merge_same_subtitle(subs)
        file_path = os.path.join(
            Path(folder_path).parent.absolute(), file_name)
        subs.sort()
        if 'zh-Hant' in file_path or 'cmn-Hant' in file_path:
            subs = format_subtitle(subs)
        subs.save(file_path)
        logger.info(file_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)


def convert_dfxp(text):
    soup = BeautifulSoup(text, 'xml')
    italic = None
    if soup.find('style', attrs={'tts:fontStyle': 'italic'}):
        italic = soup.find('style', attrs={'tts:fontStyle': 'italic'})[
            'xml:id']
    subtitles = []
    for sub in soup.find_all('p'):
        if sub['begin'] == '0t':
            start = 0
        else:
            start = int(sub['begin'].replace('t', '')[:-4])
        end = int(sub['end'].replace('t', '')[:-4])
        text = ''
        for child in sub.children:
            if child.name == 'span':
                if italic and child['style'] == italic:
                    text += f"<i>{child.text}</i>"
                else:
                    text += child.text
            if child.name == 'br':
                text += '\n'
        text = text.strip()
        subtitles.append(pysubs2.ssaevent.SSAEvent(start, end, text))
    return subtitles


def dfxp_to_srt(subtitle, subtitle_name):
    with open(subtitle, 'r') as file:
        text = file.read()
    subtitles = convert_dfxp(text)
    subs = convert_list_to_subtitle(subtitles)
    subs.sort()
    subs.save(subtitle_name)


def clean_subs(subs):
    for sub in subs:
        text = sub.text
        text = re.sub(r"&rlm;", "", text)
        text = re.sub(r"&lrm;", "", text)
        text = re.sub(r"&amp;", "&", text)
        sub.text = text.strip()

    return subs


def merge_same_subtitle(subs):
    for i, sub in enumerate(subs):
        if i > 0 and sub.text == subs[i-1].text and sub.start - subs[i-1].end <= 20:
            subs[i-1].end = sub.end
            subs.pop(i)
        elif sub.text == '':
            subs.pop(i)
    return subs


def format_subtitle(subs):
    """
    Format subtitle
    """
    for sub in subs:
        text = sub.text
        if re.search(r'[\u4E00-\u9FFF]', text):
            text = text.replace('(', '（')
            text = text.replace(')', '）')
            text = text.replace('!', '！')
            text = text.replace('?', '？')
            text = text.replace(':', '：')
            text = text.replace('...', '…')
            text = text.replace(' （', '（')
            text = text.replace('） ', '）')

            if text.count('-') == 2:
                text = text.replace('- ', '-')

            text = re.sub(r',([\u4E00-\u9FFF]+)', '，\\1', text)
            text = re.sub(r'([\u4E00-\u9FFF]+),', '\\1，', text)

        text = text.replace('  ', ' ')
        text = text.replace('  ', ' ')

        sub.text = text.strip()

    return subs


def add_simplified_chinese_subtitle(subtitles):
    if subtitles and 'zh-Hans' not in subtitles:
        traditional_chinese_subtitle = next(
            (subtitle for subtitle in subtitles if 'zh-Hant' in subtitle or 'yue' in subtitle), '')
        if traditional_chinese_subtitle:
            simplified_chinese_subtitle = traditional_chinese_subtitle.replace(
                Path(traditional_chinese_subtitle).stem.split(' ')[-1], 'zh-Hans')
            logger.info(
                "\nAdd Simplified Chinese Subtitle:\n---------------------------------------------------------------\n%s", os.path.basename(simplified_chinese_subtitle))
            with open(traditional_chinese_subtitle, 'r', encoding='utf-8') as input_file:
                traditional_chinese_subtitle = opencc.OpenCC(
                    't2s.json').convert(input_file.read())
            with open(simplified_chinese_subtitle, 'w', encoding='utf-8') as output_file:
                output_file.write(traditional_chinese_subtitle)


if __name__:
    logger = logging.getLogger(__name__)
