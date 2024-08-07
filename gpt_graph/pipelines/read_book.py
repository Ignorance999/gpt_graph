# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 15:36:21 2024

@author: User
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 20:02:42 2024

@author: User
"""
from gpt_graph.components import (
    # ddg_search,
    # WebScraper,
    TextExtractor,
    TextToSpeech,
    GoogleDriveUploader,
    YouTubeLister,
    DirFileLister,
    PDFSplitter,
    Summarizer,
    #PDFBookmarkSplitter,
    Filter,
    Saver,
)


from gpt_graph.utils.validation import validate_nodes
from gpt_graph.core.pipeline import Pipeline
from pathlib import Path
from pydantic import HttpUrl
import functools
import datetime
import os

from gpt_graph.core.decorators.component import component
# %%


class ReadBook(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filter = Filter()
        self.youtube_lister = YouTubeLister()
        self.dir_file_lister = DirFileLister()
        self.pdf_splitter = PDFSplitter()
        self.summarizer = Summarizer()
        self.saver = Saver()
        # self.webscraper = WebScraper()
        self.text_extract = TextExtractor()
        self.tts = TextToSpeech()
        # self.google_drive = GoogleDriveUploader()

        self.router = self.router()
        self.set_data = self.set_data()

        (
            self | self.router | self.filter | self.summarizer | self.saver | self.tts
            # | self.google_drive
        ) + [
            self.set_data,  # router
            self.pdf_splitter,  # router
            self.dir_file_lister,  # router
            self.youtube_lister,  # router
            # self.webscraper,  # router
            self.text_extract,  # router
        ]

        drive_folder_path = f"{self.__class__.__name__}/{datetime.date.today()}"
        output_folder = os.path.join(
            os.environ.get("OUTPUT_FOLDER"),
            self.__class__.__name__,
            f"{datetime.date.today()}",
        )
        self.set_params({"output_folder": output_folder})
        self.set_placeholders(
            {
                "[OUTPUT_FOLDER]": output_folder,
                "[DRIVE_FOLDER_PATH]": drive_folder_path,
            }
        )

        # self.__post_init__()

    @component()
    def router(self):
        nodes = self.sub_node_graph.default_get_input_nodes()

        if all(validate_nodes(nodes, type_hint="file_path")):
            # Check if all file paths are directories (indicative of folders)
            if all(os.path.isdir(node["content"]) for node in nodes):
                target_step = ["dir_file_lister", "text_extract"]  # , "step_filter"]

            # Check if all file paths end with '.pdf'
            elif all(node["content"].endswith(".pdf") for node in nodes):
                target_step = ["pdf_splitter"]
            else:
                target_step = ["text_extract"]

        elif all(validate_nodes(nodes, type_hint=HttpUrl)):
            # Check if any URL is a YouTube playlist or channel
            if any(
                "youtube.com/playlist?list=" in node["content"]
                or "youtube.com/channel/" in node["content"]
                for node in nodes
            ):
                target_step = ["youtube_lister"]
            else:
                target_step = ["webscrape"]
        else:
            target_step = "continue"

        if target_step != "continue":
            target_step.append("set_data")
            self.route_to(target_step)
            print(f"route_to: {target_step}")

    @component()
    def set_data(self, filter_cri=None):
        nodes = self.sub_node_graph.default_get_input_nodes(filter_cri)

        last_step_names = [s.base_name for s in self.sub_steps_history]
        last_step_name = last_step_names[-1]
        for i, node in enumerate(nodes):
            if (
                "dir_file_lister" in last_step_names
                and last_step_name == "text_extract"
            ):
                title_node = self.sub_node_graph.default_get_input_nodes(
                    filter_cri={"step_name": {"$regex": "dir_file_lister"}},
                    children=node,
                )[0]
                content = node["content"]
                title = f'{i:03}_{title_node["content"]}'

            elif last_step_name == "youtube_lister":
                content = node["content"]
                title = f'{node["extra"]["id"]:03}_{node["extra"]["title"]}'

            elif last_step_name == "webscrape":
                content = node["content"]
                title = f'{i:03}_{node["content"][:50]}'

            elif last_step_name == "text_extract":
                content = node["content"]
                file_path = node["extra"].get("output_file_path") or content[:20]
                title = f"{i:03}_{file_path}"

            elif last_step_name == "pdf_splitter":
                title = f'{i:03}_{node["extra"]["title"]}'
                content = node["content"]
            else:
                raise

            self.sub_node_graph.add_node(
                content=content,
                type=str,
                name="data",
                parent_nodes=node,
                extra={"title": title, "relative_id": i},
            )

        return

    def run(
        self,
        input_data=None,
        entry_list=[],
        word_limit=None,
        params={},  # {"max_token_count": 700}, #prompt, grouping_method
        **kwargs,
    ):
        params_update = {
            "word_limit": word_limit,
            "filter:filter_cri": {"extra.relative_id": lambda x: x in entry_list}
            if entry_list
            else None,
        }
        params.update(params_update)
        #'prompt': prompts_chain_read_book.MARIZE_AND_TRANSLATE_FOR_AUDIOBOOK,
        #'grouping_method':'accumulate',
        super().run(input_data=input_data, params=params, **kwargs)


# %%

if __name__ == "__main__":
    import os

    s = ReadBook(if_load_env=True)
    test_folder = os.environ.get("TEST_FOLDER")
    file_path = os.path.join(test_folder, r"inputs\accounting.pdf")
    file_path = os.path.join(test_folder, r"inputs\what_is_the_singularity_full.txt")
    result = s.run(
        input_data=file_path,
        # start_step = 6,
        # entry_list = [9,10,11,12],
        params={
            "summarizer:model_name": "test",  # "chat_gpt4o_mini",  # "chat_gpt4o_poe"
            # "filter:if_ask_user": False,
        },
        # mode="new",
    )

    # s.sub_node_graph.plot(if_pyvis=True)
    # s.sub_step_graph.plot()
    # s.graph.nodes[1]
    # # %%
    # s.save_elements("nodes")
    # s.save_elements("registered_steps")
# %%
