# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 16:09:23 2024

@author: User
"""

from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from gpt_graph.core.component import Component
from typing import List, Dict


class Retriever(Component):
    step_type = "list_to_list"
    input_schema = {
        "nodes": {"type": "node"},
    }
    cache_schema = {}
    output_schema = {"result": {"type": List[Dict]}}
    output_format = "node"

    def __init__(self, **kwargs):
        self.model = None
        self.tokenizer = None  # AutoTokenizer.from_pretrained(model_name)
        self.nodes = []
        super().__init__(**kwargs)
        # self.model = AutoModel.from_pretrained(model_name)

    def _get_embedding(self, text):
        """Creates an embedding for the given text."""
        inputs = self.tokenizer(
            text, return_tensors="pt", padding=True, truncation=True
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).cpu().numpy()

    def add_nodes(self, new_nodes):
        for node in new_nodes:
            if isinstance(node, str):
                text = node
                extra = {}
                node_dict = {"content": text, "extra": extra}
            else:
                text = node["content"]
                extra = node["extra"]
                node_dict = node

            # Check if embedding already exists in extra
            if "embedding" not in extra:
                emb = self._get_embedding(text)
                extra["embedding"] = emb

            self.nodes.append(node_dict)

    def run(
        self,
        nodes=None,
        query=None,
        model=None,
        added_nodes=None,
        top_k=1,
        lower_threshold=None,
        upper_threshold=None,
        sorted=True,
        return_scores=False,
        **kwargs,
    ):
        # Initialize model and tokenizer if model name is provided
        if self.model is None and model is None:
            model = "BAAI/bge-small-en-v1.5"

        if model is not None:
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            self.model = AutoModel.from_pretrained(model)

        # Use stored nodes if not provided
        if nodes is None:
            nodes = self.nodes
        else:
            # Use provided nodes
            self.add_nodes(nodes)
            nodes = self.nodes

        # Add new nodes if provided
        if added_nodes is not None:
            self.add_nodes(added_nodes)

        node_embeddings = [node["extra"]["embedding"] for node in nodes]

        # if query is None, do the embedding only
        if query is None:
            return nodes

        """Finds the top-k documents similar to the query or those above a similarity threshold."""
        if isinstance(query, str):
            query_text = query
        else:
            query_text = query["content"]
        query_embedding = self._get_embedding(
            query_text
        )  # Assuming this returns a 2D array

        scores = []
        for node_emb in node_embeddings:
            sim = cosine_similarity(query_embedding, node_emb)
            scores.append(sim)

        scores = [i.item() for i in scores]

        if top_k is not None:
            top_k_indices = np.argsort(scores)[-top_k:][::-1]
        elif lower_threshold is not None or upper_threshold is not None:
            if lower_threshold is None:
                lower_threshold = -np.inf  # No lower bound if not specified
            if upper_threshold is None:
                upper_threshold = np.inf  # No upper bound if not specified
            top_k_indices = np.where(
                (np.array(scores) >= lower_threshold)
                & (np.array(scores) <= upper_threshold)
            )[0]
        elif sorted:
            top_k_indices = np.argsort(scores)[::-1]
        else:
            top_k_indices = np.arange(len(scores))

        # Embedded function to create a copy of a node
        def create_copy_node(node):
            return {
                "content": node["content"],
                "extra": node["extra"],
                "parent_nodes": [node["node_id"]],
            }

        top_k_nodes = [create_copy_node(nodes[i]) for i in top_k_indices]

        # top_k_nodes = [nodes[i] for i in top_k_indices]

        if return_scores:
            top_k_scores = [scores[i] for i in top_k_indices]
            return list(zip(top_k_nodes, top_k_scores))
        else:
            return top_k_nodes


if __name__ == "__main__":
    retriever = SimilaritySearcher(cache_schema={"<SELF>": {"key": "[base_name]"}})
    documents = [
        "This is document 1",
        "This is document 2",
        {"content": "This is document 3", "extra": {}},
        "This is document 4",
        {"content": "This is document 5", "extra": {}},
    ]

    query = "docum4ent"
    # # model_name = "distilbert-base-uncased"  # Replace with your desired model name
    # model_name = None

    # # Add documents to the retriever
    # # retriever.add_nodes(documents)

    # print("Searching with return_scores=True:")
    # results_with_scores = retriever.run(
    #     query, nodes=documents, model=model_name, top_k=3, return_scores=True
    # )
    # for doc, score in results_with_scores:
    #     print(f"Document: {doc}, Score: {score}")

    # print("\nSearching with return_scores=False:")
    # results_without_scores = retriever.run(
    #     query, model=model_name, top_k=1, return_scores=False
    # )
    # for doc in results_without_scores:
    #     print(f"Document: {doc}")
    # %%

    from gpt_graph.core.pipeline import Pipeline

    p = Pipeline()
    p | retriever
    p.run(input_data=documents, params={"query": query, "top_k": 2})
