from gpt_graph.components.combiners.text_combiner import TextCombiner
from gpt_graph.core.pipeline import Pipeline
from gpt_graph.components.dir_file_lister import DirFileLister
from gpt_graph.components.filter import Filter
from gpt_graph.components.llm import LLMModel
from gpt_graph.components.transformers.node_to_str import NodeToStr
from gpt_graph.components.text_extractor import TextExtractor
from gpt_graph.components.parsers.text_to_bool_parser import TextToBoolParser
from gpt_graph.components.transformers.prompt_formatter import PromptFormatter
from gpt_graph.components.operators.file_copier import FileCopier
from gpt_graph.components.retriever import Retriever
from gpt_graph.components.summarizer import Summarizer
from gpt_graph.components.combiners.text_combiner import TextCombiner
from gpt_graph.components.saver import Saver


class RAG(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dir_file_lister = DirFileLister()
        self.text_extractor = TextExtractor()
        self.prompt_formatter = PromptFormatter()
        self.llm = LLMModel()
        # self.text_to_bool_parser = TextToBoolParser()
        self.filter = Filter()
        # self.node_to_str = NodeToStr()
        # self.file_copier = FileCopier()
        self.retriever = Retriever()
        self.summarizer = Summarizer()
        self.text_combiner = TextCombiner()
        self.saver = Saver()

        (
            self
            | self.dir_file_lister
            | self.text_extractor
            | self.retriever
            | self.summarizer
            | self.text_combiner
            | self.prompt_formatter
            | self.llm
            # | self.text_to_list_parser
            | self.filter
            | self.prompt_formatter
            | self.llm
            | self.saver
            # | self.prompt_formatter
            # | self.llm
            # | self.text_to_bool_parser
            # | self.filter
            # | self.file_copier
        ) + []

        self.__post_init__()

        prompt_summary = """
        summarize the following in 1 paragraph within 50 words. A whole paragraph please. very short paragraph of 50 words. Dont give me a outline.
        ```
        {context}
        ```
        """
        params = {
            "dir_file_lister:recursive": True,
            "dir_file_lister:regex_pattern": r".*\.txt$",
            "text_extractor:word_limit": 1200,  # Limit to 1000 words
            "text_combiner:id_format": "<ID: {}>",
            "text_combiner:separator": r"\n------------------------------------\n",
            # "text_combiner:max_length": 100,
            "prompt_formatter.0:field_name1": "context",
            "llm:wait_time": 0.5,
            "llm.0:output_type": "list",
            "llm.0:<UPDATE_STEP_TYPE>": "node_to_node",
            # "llm.0:<>": "list",
            "filter:<UPDATE_INPUT_SCHEMA>": {
                "filter_nodes": {"type": "node"},
                "indices": {
                    "filter_cri": {"step_name": {"$regex": "llm.0"}},
                    "dim": 0,
                },
            },
            "filter:nodes": {"step_name": {"$regex": "text_extractor", "$order": -1}},
            "filter:filter_nodes": {"step_name": {"$regex": "retriever", "$order": -1}},
            "filter:filter_cri": {"node_id": {"$order": "[indices]"}},
            "retriever:top_k": 3,
            "prompt_formatter.1:field_name1": "context",
            "llm.0:model_name": "chat_gpt4o_mini",  # "test",
            "llm.1:model_name": "chat_gpt4o_mini",  # "test",
            "summarizer:model_name": "groq",  # "test",
            "summarizer:prompt": prompt_summary,  # "test",
            "saver:output_folder": os.environ.get("OUTPUT_FOLDER"),
            # "model_name":"groq_tool",
            # "llm.1:output_format": "list",
        }
        self.set_params(raw_params=params)

    def run(
        self,
        folder_path=None,
        prompt="",
        params={},  # {"max_token_count": 700}, #prompt, grouping_method
        **kwargs,
    ):
        prompt2 = f"""
        there are several items in the following, which of these you do think are helpful in answering the following question? ```quest: {prompt}```
        ------
        your answer should be a list of IDs(list of int). And you should use tool calling to do this.
        example output:
        [1,3]
        ------
        context: 
        {{context}}        
        """
        prompt3 = f"""
        {prompt}, 
        you can refer to the following information:
        {{context}}        
        """

        params_update = {
            "retriever:query": prompt,
            "prompt_formatter.0:prompt": prompt2,
            "prompt_formatter.1:prompt": prompt3,
        }
        params.update(params_update)
        super().run(input_data=folder_path, params=params, **kwargs)


if __name__ == "__main__":
    import os

    p = RAG(if_load_env=True)
    folder_path = os.path.join(os.environ.get("TEST_FOLDER"), "inputs", "pp_rag")
    prompt = (
        "What are the latest advancements in technology?, i am talking about physics"
    )
    result = p.run(folder_path=folder_path, prompt=prompt)
    print(result)
    # print("Useful insurance PDF file paths:", result)
    p.sub_node_graph.plot(if_pyvis=True)
    # p.sub_node_graph.show_nodes_by_attr("step_name")
    # p.sub_node_graph.graph.nodes[603]
    # p.sub_node_graph.save()
