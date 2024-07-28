# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 11:51:57 2024

@author: User
"""

from PyPDF2 import PdfReader
from gpt_graph.components.splitters.text_splitter import TextSplitter
from typing import Any
from typing import Any, List, Dict


class PDFBookmarkSplitter:
    step_type = "node_to_list"
    input_schema = {"input_file_path": {"type": "file_path"}}
    output_schema = {"extracted_text": {"type": Any}}  # or dict list

    def run(self, input_file_path: str) -> List[Dict]:
        """
        Splits the PDF by bookmarks (if available) and extracts text from each bookmarked section or the entire document.
        Returns a list of dictionaries with each dictionary containing the "content" of the text and "extra" details like the title.
        """
        self.input_file_path = input_file_path
        reader = PdfReader(self.input_file_path)
        bookmarks = self._get_bookmarks(reader)
        results = []

        if bookmarks:  # Process each bookmark
            for title, page_numbers in bookmarks.items():
                text_content = ""
                for page_number in page_numbers:
                    page = reader.pages[page_number]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
                results.append({"content": text_content.strip(), "title": title})
        else:  # No bookmarks, process the entire document
            text_content = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n\n"
            results.append({"content": text_content.strip(), "title": "Full Document"})

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
                page_number = reader.get_page_number(page)
                if title in results:
                    results[title].append(page_number)
                else:
                    results[title] = [page_number]

        return results


# %%

# Example usage:
if __name__ == "__main__":
    import os

    file_path = os.path.join(os.getcwd(), r"..\..\tests\inputs\EU import 2019.pdf")
    splitter = PDFBookmarkSplitter()
    result = splitter.run(file_path)
    # print(result)
