# -*- coding: utf-8 -*-
"""
Created on Thu Apr 11 22:51:35 2024

@author: User
"""

from typing import Dict
from gtts import gTTS
import os
from gpt_graph.core.component import Component

# from langdetect import detect, DetectorFactory
from pydub import AudioSegment
import io
import re
# DetectorFactory.seed = 0

import os

path_ffmpeg = os.environ.get("FFMPEG_PATH")
if path_ffmpeg is None:
    from gpt_graph.utils.load_env import load_env

    load_env()
    path_ffmpeg = os.environ.get("FFMPEG_PATH")

os.environ["PATH"] += os.pathsep + path_ffmpeg


class TextToSpeech(Component):
    step_type = "node_to_node"
    input_schema = {"text": {"type": str}}
    cache_schema = {}
    output_schema = {"output_file_path": {"type": "file_path"}}
    output_format = "plain"

    def run(
        self,
        text=None,
        if_input_file_path=False,
        used_language=None,  # "zh"
        output_file_path=None,
        speed=1.2,
        tts_engine="gtts",
    ) -> Dict:
        """
        Convert text to speech. If `if_input_file_path` is True, then `text` is expected to be a file path
        from which text will be read. The output will be saved as an audio file.

        :param text: Text string or a path to a text file if `if_input_file_path` is True.
        :param if_input_file_path: Boolean indicating if `text` should be treated as a file path.
        :param output_file_path: Path where the audio file should be saved.
        :param speed: Playback speed factor; values > 1 for faster, < 1 for slower.
        :return: Dict with the path to the saved audio file.
        """
        if if_input_file_path:
            if text is None or not os.path.exists(text):
                raise ValueError(
                    "File path must be provided and must exist when if_input_file_path is True"
                )
            if output_file_path is None:
                output_file_path = text.replace(".txt", ".mp3")
            with open(text, "r", encoding="utf-8") as file:
                text = file.read()
        self.output_file_path = output_file_path
        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")

        if tts_engine == "gtts":
            self._process_with_gtts(text, used_language, output_file_path, speed)
        elif tts_engine == "pytts":
            self._process_with_pyttsx3(text, used_language, output_file_path, speed)
        else:
            raise ValueError("Unsupported TTS engine")

        return output_file_path

    def _process_with_gtts(self, text, used_language, output_file_path, speed):
        words = text.split()
        combined_audio = AudioSegment.empty()
        sentence = ""
        language = None

        for idx, word in enumerate(words + [""]):  # Process the last batch
            if not word.strip() and idx != len(words):
                continue

            if used_language is None:
                word_language = self._detect_language(word, language)
            else:
                word_language = used_language

            if word_language == language:
                sentence += " " + word
            else:
                if sentence:
                    combined_audio += self._process_sentence(sentence, language, speed)

                sentence = word + " " if word.strip() else ""
                language = word_language

        if sentence:
            combined_audio += self._process_sentence(sentence, language, speed)

        combined_audio.export(self.output_file_path, format="mp3")
        print(f"Saved audio at: {output_file_path}")
        return output_file_path

    def _process_with_pyttsx3(self, text, used_language, output_file_path, speed):
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", engine.getProperty("rate") * speed)
        # Setting the voice property based on language needs careful implementation
        voices = engine.getProperty("voices")
        for voice in voices:
            if used_language in voice.languages:
                engine.setProperty("voice", voice.id)
                break
        engine.save_to_file(text, output_file_path)
        engine.runAndWait()
        return output_file_path

    def _process_sentence(self, sentence, language, speed, tts_engine="gtts"):
        """
        Convert a sentence to speech and return the audio segment.

        :param sentence: The sentence to convert.
        :param language: The language of the sentence.
        :param speed: Playback speed factor.
        :return: Audio segment.
        """
        if tts_engine == "gtts":
            tts = gTTS(text=sentence.strip(), lang=language, slow=False)
            with io.BytesIO() as audio_io:
                tts.write_to_fp(audio_io)
                audio_io.seek(0)
                audio_segment = AudioSegment.from_file(audio_io, format="mp3")
                if speed != 1.0:
                    audio_segment = audio_segment.speedup(playback_speed=speed)

        else:
            raise ValueError("Unsupported TTS engine")

        return audio_segment

    def _detect_language(self, word, previous_language):
        """
        Custom language detection to handle specific logic for Chinese characters and number transitions.

        :param word: The word to analyze.
        :param previous_language: The last detected language.
        :return: Detected language.
        """
        if re.search("[\u4e00-\u9fff]", word):
            return "zh"
        elif re.match("^\d+$", word) and previous_language:
            return previous_language  # Continue with the previous language if the word is only numbers
        else:
            return "en"


# Example usage of the component is omitted for brevity.


# tts = gTTS(text=text, lang=lang)
# tts.save(output_file_path)

# Example usage:
# Make sure to replace 'Your actual text here' with the text you want to convert to speech.
# %%
if __name__ == "__main__":
    text_extractor = TextToSpeech()
    output_folder = os.environ.get("OUTPUT_FOLDER")
    result = text_extractor.run(
        text=r"測試haha i like you",  # "",
        used_language="zh",
        tts_engine="pytts",
        speed=1.0,
        output_file_path=os.path.join(
            output_folder,
            r"test3.mp3",
        ),
    )
