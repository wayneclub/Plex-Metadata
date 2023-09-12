
#!/usr/bin/python3
# coding: utf-8

"""
This module is to handle mux media streams.
"""
import re
import os
import sys
import shutil
import logging
import subprocess
import contextlib
import glob
from pymediainfo import MediaInfo
from configs.config import Config


class Muxer(object):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.current_name_original = kwargs.get("title", None)
        self.current_name = kwargs.get("title", None)
        self.season_folder = kwargs.get("folder_path", None)
        self.current_heigh = kwargs.get("max_height", None)
        self.current_width = kwargs.get("max_width", None)
        self.source_tag = kwargs.get("source", None)
        self.output_video = self.current_name_original

        self.config = Config()
        self.language_list = self.config.language_list()

        os.chdir(self.season_folder)
        self.audio_profile = self.get_audio_id()  # kwargs.get("audio_profile", None)
        self.video_profile = self.get_video_id()  # kwargs.get("video_profile", None)
        self.mkvmerge = self.config.bin()["mkvmerge"]
        self.merge = []
        self.muxer_settings = self.config.muxer()

        ##############################################################################

        self.extra_output_folder = self.season_folder
        self.group = self.muxer_settings["group_name"]
        self.muxer_scheme = self.muxer_settings["scheme"]

        self.scheme = self.muxer_settings["schemeslist"][self.muxer_scheme]
        self.extras = self.muxer_settings["extra_cmd"]
        self.fps24 = True if self.source_tag in self.muxer_settings["fps24"] else False
        self.default_mux = True if self.muxer_settings["default"] else False
        self.prepare_muxer()

    def is_extra_folder(self):
        extra_folder = None
        if self.extra_output_folder:
            if not os.path.isabs(self.extra_output_folder):
                raise ValueError("Error you should provide full path dir: {}.".format(
                    self.extra_output_folder))
            if not os.path.exists(self.extra_output_folder):
                try:
                    os.makedirs(self.extra_output_folder)
                except Exception as e:
                    raise ValueError("Error when create folder dir [{}]: {}.".format(
                        e, self.extra_output_folder))
            extra_folder = self.extra_output_folder
            return extra_folder

        if self.muxer_settings["mkv_folder"]:
            if not os.path.isabs(self.muxer_settings["mkv_folder"]):
                raise ValueError("Error you should provide full path dir: {}.".format(
                    self.muxer_settings["mkv_folder"]))
            if not os.path.exists(self.muxer_settings["mkv_folder"]):
                try:
                    os.makedirs(self.muxer_settings["mkv_folder"])
                except Exception as e:
                    raise ValueError("Error when create folder dir [{}]: {}.".format(
                        e, self.muxer_settings["mkv_folder"]))
            extra_folder = self.muxer_settings["mkv_folder"]
            return extra_folder

        return extra_folder

    def prepare_muxer(self):
        if self.muxer_settings["no_title"]:
            self.current_name = self.no_title()

        extra_folder = self.is_extra_folder()

        if extra_folder:
            self.season_folder = extra_folder
        else:
            if not self.default_mux:
                if self.season_folder:
                    self.season_folder = self.set_folder()
        return

    def sort_files_by_size(self):
        file_list = []
        audio_tracks = (
            glob.glob(f"{self.current_name_original}*.eac3")
            + glob.glob(f"{self.current_name_original}*.ac3")
            + glob.glob(f"{self.current_name_original}*.aac")
            + glob.glob(f"{self.current_name_original}*.m4a")
            + glob.glob(f"{self.current_name_original}*.dts")
        )
        if audio_tracks == []:
            raise FileNotFoundError("no audio files found")

        for file in audio_tracks:
            file_list.append({"file": file, "size": os.path.getsize(file)})

        file_list = sorted(file_list, key=lambda k: int(k["size"]))
        return file_list[-1]["file"]

    def get_video_file(self):
        video_file = glob.glob(f"{self.current_name_original}*.mp4")

        if not video_file:
            raise ValueError("No Video file in Dir...")

        return video_file[-1]

    def get_video_id(self):
        video_file = self.get_video_file()

        media_info = MediaInfo.parse(video_file)
        track = [
            track for track in media_info.tracks if track.track_type == "Video"][0]

        if track.format == "AVC":
            if track.encoding_settings:
                return "x264"
            return "H264"
        elif track.format == "HEVC":
            if track.commercial_name == "HDR10" and track.color_primaries:
                return "HDR.HEVC"
            if track.commercial_name == "HEVC" and track.color_primaries:
                return "HEVC"

            return "DV.HEVC"

        return None

    def get_audio_id(self):
        audio_id = None
        media_info = MediaInfo.parse(self.sort_files_by_size())
        track = [
            track for track in media_info.tracks if track.track_type == "Audio"][0]

        if track.format == "E-AC-3":
            audio_codec = "DDP"
        elif track.format == "AC-3":
            audio_codec = "DD"
        elif track.format == "AAC":
            audio_codec = "AAC"
        elif track.format == "DTS":
            audio_codec = "DTS"
        elif "DTS" in track.format:
            audio_codec = "DTS"
        else:
            audio_codec = "DDP"

        if track.channel_s == 8:
            channels = "7.1"
        elif track.channel_s == 6:
            channels = "5.1"
        elif track.channel_s == 2:
            channels = "2.0"
        elif track.channel_s == 1:
            channels = "1.0"
        else:
            channels = "5.1"

        audio_id = (
            f"{audio_codec}{channels}.Atmos"
            if "Atmos" in track.commercial_name
            else f"{audio_codec}{channels}"
        )

        return audio_id

    def heigh(self):
        try:
            width = int(self.current_width)
            heigh = int(self.current_heigh)
        except Exception:
            return self.current_heigh

        res1080p = "1080p"
        res720p = "720p"
        sd = ""

        if width >= 3840:
            return "2160p"

        if width >= 2560:
            return "1440p"

        if width > 1920:
            if heigh > 1440:
                return "2160p"
            return "1440p"

        if width == 1920:
            return res1080p
        elif width == 1280:
            return res720p

        if width >= 1400:
            return res1080p

        if width < 1400 and width >= 1100:
            return res720p

        if heigh == 1080:
            return res1080p
        elif heigh == 720:
            return res720p

        if heigh >= 900:
            return res1080p

        if heigh < 900 and heigh >= 700:
            return res720p

        return sd

    def no_title(self):
        regex = re.compile("(.*) [S]([0-9]+)[E]([0-9]+)")
        if regex.search(self.current_name):
            return regex.search(self.current_name).group(0)

        return self.current_name

    def run(self, command):
        self.logger.debug("muxing command: %s", " ".join(command))

        def unbuffered(proc, stream="stdout"):
            newlines = ["\n", "\r\n", "\r"]
            stream = getattr(proc, stream)
            with contextlib.closing(stream):
                while True:
                    out = []
                    last = stream.read(1)
                    # Don't loop forever
                    if last == "" and proc.poll() is not None:
                        break
                    while last not in newlines:
                        # Don't loop forever
                        if last == "" and proc.poll() is not None:
                            break
                        out.append(last)
                        last = stream.read(1)
                    out = "".join(out)
                    yield out

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        self.logger.info("\nStart Muxing...")
        for line in unbuffered(proc):
            if "Progress:" in line:
                sys.stdout.write("\r%s" % (line))
                sys.stdout.flush()
            elif "Multiplexing" in line:
                sys.stdout.write("\r%s" %
                                 (line.replace("Multiplexing", "Muxing")))
                sys.stdout.flush()
            elif "Error" in line:
                sys.stdout.write("\r%s" % (line))
                sys.stdout.flush()

        self.logger.info("")

    def set_name(self):

        output_video = (self.scheme.replace("{t}", self.rename_file_name(self.current_name))
                        .replace("{r}", self.heigh())
                        .replace("{s}", self.source_tag)
                        .replace("{ac}", self.audio_profile)
                        .replace("{vc}", self.video_profile))
        if self.group:
            output_video = output_video.replace("{gr}", self.group)
        else:
            output_video = output_video.replace("-{gr}", "")

        for i in range(10):
            output_video = re.sub(r"(\.\.)", ".", output_video)

        if self.season_folder:
            output_video = os.path.join(
                os.path.abspath(self.season_folder), output_video)
            output_video = output_video.replace("\\", "/")

        return f"{output_video}.mkv"

    def set_folder(self):
        folder = (
            self.scheme.replace(
                "{t}", self.rename_file_name(self.season_folder)
            )
            .replace("{r}", self.heigh())
            .replace("{s}", self.source_tag)
            .replace("{ac}", self.audio_profile)
            .replace("{vc}", self.video_profile)
            .replace("{gr}", self.group)
        )

        for i in range(10):
            folder = re.sub(r"(\.\.)", ".", folder)

        return folder

    def extra_language_list(self):
        extra_language_list = [
            ["Polish - Dubbing", "pol", "pol", "Polish - Dubbing"],
            ["Polish - Lektor", "pol", "pol", "Polish - Lektor"],
        ]

        return extra_language_list

    def add_chapters(self):
        if os.path.isfile(self.current_name_original + " Chapters.txt"):
            self.merge += [
                "--chapter-charset",
                "UTF-8",
                "--chapters",
                self.current_name_original + " Chapters.txt",
            ]

        return

    def add_video(self):
        input_video = None

        input_video = self.get_video_file()

        if self.default_mux:
            output_video = (
                re.compile("|".join([".h264", ".h265", ".vp9", ".mp4"])).sub(
                    "", input_video)
                + ".mkv"
            )
            if self.season_folder:
                output_video = os.path.join(
                    os.path.abspath(self.season_folder), output_video
                )
                output_video = output_video.replace("\\", "/")
        else:
            output_video = self.set_name()

        self.output_video = output_video

        video_title = (self.scheme.replace("{t}", self.rename_file_name(self.current_name))
                       .replace("{r}", self.heigh())
                       .replace("{s}", self.source_tag)
                       .replace("{ac}", self.audio_profile)
                       .replace("{vc}", self.video_profile)
                       )

        if self.group:
            video_title = video_title.replace("{gr}", self.group)
        else:
            video_title = video_title.replace("-{gr}", "")

        for i in range(10):
            video_title = re.sub(r"(\.\.)", ".", video_title)

        if self.fps24:
            self.merge += [
                self.mkvmerge,
                "--output",
                output_video,
                "--default-duration",
                "0:24000/1001p",
                "--language",
                "0:und",
                "--default-track",
                "0:yes",
                "(",
                input_video,
                ")",
            ]
        else:
            self.merge += [
                self.mkvmerge,
                "--output",
                output_video,
                "--title",
                video_title,
                "(",
                input_video,
                ")",
            ]

        return

    def add_audio(self):

        # audiofiles = [
        #     "{} {}.ac3",
        #     "{} {} - Audio Description.ac3",
        #     "{} {}.eac3",
        #     "{} {} - Audio Description.eac3",
        #     "{} {}.aac",
        #     "{} {} - Audio Description.aac",
        #     "{} {}.m4a",
        #     "{} {} - Audio Description.m4a",
        # ]

        audio_tracks = (
            glob.glob(f"{self.current_name_original}*.eac3")
            + glob.glob(f"{self.current_name_original}*.ac3")
            + glob.glob(f"{self.current_name_original}*.aac")
            + glob.glob(f"{self.current_name_original}*.m4a")
            + glob.glob(f"{self.current_name_original}*.dts")
        )

        for (audio_language, subs_language, language_id, language_name,) in (
                self.language_list + self.extra_language_list()
        ):
            for filename in audio_tracks:
                if audio_language in filename:
                    self.merge += [
                        "--language",
                        f"0:{language_id}",
                        "--track-name",
                        "0:Audio Description" if 'Audio Description' in filename
                        else f"0:{language_name}",
                        "--default-track",
                        "0:yes"
                        if subs_language == self.muxer_settings["default_audio_language"]
                        else "0:no",
                        "(",
                        filename,
                        ")",
                    ]

        return

    def add_subtitles(self):

        srts = [
            "{} {}.srt",
        ]
        forceds = [
            "{} forced-{}.srt",
        ]
        sdhs = [
            "{} sdh-{}.srt",
        ]

        for (
                audio_language,
                subs_language,
                language_id,
                language_name,
        ) in self.language_list:
            for subtitle in srts:
                filename = subtitle.format(
                    self.current_name_original, subs_language)
                if os.path.isfile(filename):
                    self.merge += [
                        "--language",
                        f"0:{language_id}",
                        "--track-name",
                        f"0:{language_name}",
                        "--forced-track",
                        "0:no",
                        "--default-track",
                        "0:yes"
                        if subs_language == self.muxer_settings["default_subtitle_language"]
                        else "0:no",
                        "--compression",
                        "0:none",
                        "(",
                        filename,
                        ")",
                    ]

            for subtitle in forceds:
                filename = subtitle.format(
                    self.current_name_original, subs_language)
                if os.path.isfile(filename):
                    self.merge += [
                        "--language",
                        f"0:{language_id}",
                        "--track-name",
                        "0:Forced",
                        "--forced-track",
                        "0:yes",
                        "--default-track",
                        "0:no",
                        "--compression",
                        "0:none",
                        "(",
                        filename,
                        ")",
                    ]

            for subtitle in sdhs:
                filename = subtitle.format(
                    self.current_name_original, subs_language)
                if os.path.isfile(filename):
                    self.merge += [
                        "--language",
                        f"0:{language_id}",
                        "--track-name",
                        "0:SDH",
                        "--forced-track",
                        "0:no",
                        "--default-track",
                        "0:no",
                        "--compression",
                        "0:none",
                        "(",
                        filename,
                        ")",
                    ]

        return

    def rename_file_name(self, filename):

        filename = (
            filename.replace(" ", ".")
            .replace("'", "")
            .replace('"', "")
            .replace(",", "")
            .replace("-", "")
            .replace(":", "")
            .replace("’", "")
            .replace('"', '')
            .replace("-.", ".")
            .replace(".-.", ".")
        )
        filename = re.sub(" +", ".", filename)
        for i in range(10):
            filename = re.sub(r"(\.\.)", ".", filename)

        return filename

    def start_mux(self):
        self.add_video()
        self.add_audio()
        self.add_subtitles()
        self.add_chapters()
        if not os.path.isfile(self.output_video):
            self.run(self.merge + self.extras)

        tracks = glob.glob(f"{self.current_name_original}*.eac3") \
            + glob.glob(f"{self.current_name_original}*.ac3") \
            + glob.glob(f"{self.current_name_original}*.aac") \
            + glob.glob(f"{self.current_name_original}*.m4a") \
            + glob.glob(f"{self.current_name_original}*.dts") \
            + glob.glob(f"{self.current_name_original}*.mp4") \
            + glob.glob(f"{self.current_name_original}*.vtt") \
            + glob.glob("dash*") \
            + glob.glob("*.st")

        if self.muxer_settings['keep_subtitle_language']:
            keep_subs = self.muxer_settings['keep_subtitle_language'].split(
                ',')

            for sub in glob.glob(f"{self.current_name_original}*.srt"):
                if not any(keep_sub in sub for keep_sub in keep_subs):
                    tracks.append(sub)
        else:
            tracks += glob.glob(f"{self.current_name_original}*.srt")

        for track in tracks:
            if os.path.isdir(track):
                shutil.rmtree(track)
            else:
                os.remove(track)
        os.chdir("../..")

        return self.output_video
