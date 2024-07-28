# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 11:51:57 2024

@author: User
"""

from PyPDF2 import PdfReader
from gpt_graph.components.splitters.text_splitter import TextSplitter
from typing import Any
from gpt_graph.core.component import Component


class PDFSplitter(Component):
    step_type = "node_to_list"
    input_schema = {"input_file_path": {"type": "file_path"}}
    output_schema = {"extracted_text": {"type": "node_like"}}  # or dict list
    output_format = "node_like"

    def run(self, input_file_path, max_tokens_per_item=None):
        """
        Splits the PDF by bookmarks (if available) and by max_tokens_per_item if specified.
        Returns a list of dictionaries with the structure: [{'content': text, 'extra': {'title': title}}].
        """
        self.input_file_path = input_file_path
        reader = PdfReader(self.input_file_path)
        bookmarks = self._get_bookmarks(reader)
        text_splitter = TextSplitter()
        results = []

        def process_segment(text, title, results=results):
            # Always use text_splitter to process the text
            segments = text_splitter.run(text=text, max_tokens=max_tokens_per_item)

            for index, segment in enumerate(segments):
                segment_title = f"{title}_{index}" if len(segments) > 1 else title
                results.append({"content": segment, "extra": {"title": segment_title}})

        num_pages = len(reader.pages)

        if bookmarks:
            bookmark_list = sorted(bookmarks.items(), key=lambda x: x[1][0])
            last_end_page = 0

            # Process the first part without a bookmark if it exists
            if bookmark_list[0][1][0] > 0:
                text_content = ""
                for page_num in range(0, bookmark_list[0][1][0]):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
                process_segment(text_content.strip(), "Introduction")

            for i, (title, page_numbers) in enumerate(bookmark_list):
                start_page = page_numbers[0]
                end_page = (
                    bookmark_list[i + 1][1][0] - 1
                    if i + 1 < len(bookmark_list)
                    else num_pages - 1
                )

                text_content = ""
                for page_num in range(start_page, end_page + 1):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
                process_segment(text_content.strip(), title)

                last_end_page = end_page

        else:  # No bookmarks, process the entire document
            text_content = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n\n"
            process_segment(text_content.strip(), "Full Document")

        return results

    def _get_bookmarks(self, reader, outline=None, results=None, parent_title=""):
        """
        Recursively retrieves all the bookmarks from the PDF and maps titles to page numbers.
        """
        if outline is None:
            outline = reader.outline
        if results is None:
            results = {}

        for item in outline:
            if isinstance(item, list):
                # Recursive call to handle sub-bookmarks
                self._get_bookmarks(reader, item, results, parent_title)
            else:
                title = f"{parent_title}/{item.title}" if parent_title else item.title
                page = item.page
                page_number = reader.get_page_number(page) if page is not None else 0
                if title in results:
                    results[title].append(page_number)
                else:
                    results[title] = [page_number]

        return results


# Example usage:
if __name__ == "__main__":
    import os

    test_folder = os.environ.get("TEST_FOLDER")
    file_path = os.path.join(test_folder, r"inputs/accounting.pdf")
    splitter = PDFSplitter()
    result = splitter.run(file_path, max_tokens_per_item=None)
    # print(result)
    # %%
