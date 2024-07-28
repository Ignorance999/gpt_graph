# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 16:09:46 2024

@author: User
"""

from gpt_graph.core.component import Component

# from gpt_graph.core.decorator import step, retry, skip_if_exist
import gpt_graph.prompts.prompts_step_summary as prompts
# import gpt_graph.components.functions as functions

# functions to be added to gpt_graph classes
import gpt_graph.utils.utils as utils
from gpt_graph.components.llm import LLMModel
from gpt_graph.utils.debug import logger_debug
from typing import Any, List, Dict, Optional, Union
from gpt_graph.core.graph import Graph


# %%
class Summarizer(Component, Graph):
    # Class variables
    step_type = ["node_to_node", "list_to_node"]
    input_schema = {"nodes": {"type": "node"}}
    cache_schema = {
        "llm_model": {
            "type": LLMModel,
            "default": lambda model_name: LLMModel(model_name),
        }
    }
    output_schema = {"result": {"type": List[Dict[str, Any]]}}
    output_format = "graph"

    def __init__(self, **kwargs):
        # NOTE: have to use super instead of Component, because if using Component, its run method is not self.run, but Component.run
        super().__init__(**kwargs)
        Graph.__init__(self)

    # @step(cache={"llm_model": lambda model_name: LLMModel(model_name)})
    def run(
        self,
        nodes: [List[Dict[str, Any]]] = None,
        max_token_count: int = 2000,
        prompt: str = prompts.PROMPT_OUTLINE,
        prompt_params: Optional[Dict[str, Any]] = None,
        model_name: str = "mixtral",
        grouping_method: str = "recursive",  # or "accumulate"
        min_compression_ratio: List[Optional[int]] = [None, 2],
        llm_model: Optional[LLMModel] = None,
        step_type: str = "node_to_node",
        chunk_size: Optional[int] = None,
        verbose: bool = True,
        split_method: str = "token_count",  # New parameter: "token_count" or "newline"
        **kwargs,
    ) -> List[Dict[str, Any]]:
        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            self.add_node(**node)

        self.step_type = step_type or self.step_type

        if llm_model is None:
            llm_model = LLMModel(model_name)
        else:
            llm_model.chg_curr_model(model_name=model_name)

        grouping_method = grouping_method or "recursive"
        # nodes = self.default_get_input_nodes(nodes)

        if chunk_size is None:
            chunk_size = int(max_token_count / 8)

        split_nodes = []
        for node in nodes:
            if split_method == "token_count":
                if utils.num_tokens_from_string(node["content"]) > max_token_count:
                    split_texts = utils.split_text_by_token_count(
                        node["content"], max_token_count, chunk_size
                    )
                    for text in split_texts:
                        split_node = self.add_node(
                            content=text,
                            type=str,
                            name="split_text",
                            parent_nodes=node,
                            if_output=False,
                        )
                        split_nodes.append(split_node)
                else:
                    split_nodes.append(node)
            elif split_method == "newline":
                split_texts = node["content"].split("\n")
                for text in split_texts:
                    if text.strip():  # Ignore empty lines
                        split_node = self.add_node(
                            content=text,
                            type=str,
                            name="split_text",
                            parent_nodes=node,
                            if_output=False,
                        )
                        split_nodes.append(split_node)
            else:
                raise ValueError(
                    "Invalid split_method. Choose 'token_count' or 'newline'."
                )

        groups = utils.group_strings_by_token_count(
            split_nodes,
            max_token_count,
            min_compression_ratio=min_compression_ratio[0],
        )
        logger_debug("groups has char:", [len(g) for g in groups])

        summary_node_list = []
        for group in groups:
            group_texts = "\n".join([node["content"] for node in group])
            if verbose:
                logger_debug(
                    "this group token has:",
                    utils.num_tokens_from_string(group_texts),
                )
            node_name = "top_summary" if len(groups) == 1 else "summary"

            if prompt_params is None:
                prompt_params = {"context": group_texts}
            else:
                prompt_params["context"] = group_texts

            formatted_prompt = prompt.format(**prompt_params)
            group_summary, messages = llm_model.run(
                input_data=formatted_prompt,
                model_name=model_name,
                if_return_prompt=True,
            )

            summary_node = self.add_node(
                content=group_summary,
                type=str,
                name=node_name,
                parent_nodes=group,
                extra={"prompt": messages},
                if_output=len(groups) == 1,
            )
            summary_node_list.append(summary_node)

        if len(summary_node_list) > 1:
            if grouping_method == "recursive":
                logger_debug(
                    "called another step_summarize, len of summary node list:",
                    len(summary_node_list),
                )
                return self.run(
                    nodes=summary_node_list,
                    max_token_count=max_token_count,
                    model_name=model_name,
                    llm_model=llm_model,
                    prompt=prompt,
                    prompt_params=prompt_params,
                    step_type="list_to_node",
                    grouping_method=grouping_method,
                    min_compression_ratio=min_compression_ratio
                    if len(min_compression_ratio) == 1
                    else min_compression_ratio[1:],
                    chunk_size=chunk_size,
                    verbose=verbose,
                    **kwargs,
                )
            elif grouping_method == "accumulate":
                top_summary = "\n".join([node["content"] for node in summary_node_list])
                top_summary_node = self.add_node(
                    content=top_summary,
                    type=str,
                    name="top_summary",
                    parent_nodes=summary_node_list,
                    if_output=True,
                )
                return self.graph  # [top_summary_node]
        else:
            return self.graph  # summary_node_list

        # return []


# %%
if __name__ == "__main__":
    import os
    from gpt_graph.utils.load_env import load_env

    load_env()
    from gpt_graph.core.pipeline import Pipeline

    gpt_graph_folder = os.getenv("GPT_GRAPH_FOLDER")

    file_path = os.path.join(
        gpt_graph_folder,
        r"tests\inputs\what_is_the_singularity_full.txt",
        # gpt_graph_folder,
        # r"tests\inputs\dummy_lines.txt",
    )
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    p = Pipeline()
    p | Summarize()
    result = p.run(
        # model_name = "test",
        input_data=content,
        params={
            "prompt": "summarize the following as outlines: {context}",
            "prompt_params": {"topic": "AI impact on insurance"},
            "model_name": "test",
            # "model_name": "chat_gpt3_poe",
            "step_type": "node_to_node",
            # "split_method": "newline",
            "max_token_count": 2000,
        },
    )  # chat_gpt4_poe
    # p.sub_node_graph.plot(if_pyvis=True)
    p.get_rel_graph(if_plot=True)
