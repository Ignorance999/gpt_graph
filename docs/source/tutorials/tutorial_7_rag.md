# Tutorial 7: RAG

## Overview

The RAG class is inherited from Pipeline class. It's designed to process PDF files, extract text, summarize content, filter using embedding vectors, and then answer questions based on filtered results. 

Note: You can refer to `gpt_graph/pipelines/rag.py` for the complete code.

## Class Structure

````python
class RAG(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dir_file_lister = DirFileLister()
        self.text_extractor = TextExtractor()
        self.prompt_formatter = PromptFormatter()
        self.llm = LLMModel()
        self.filter = Filter()
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
            | self.filter
            | self.prompt_formatter
            | self.llm
            | self.saver
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
            "text_extractor:word_limit": 1200,  
            "text_combiner:id_format": "<ID: {}>",
            "text_combiner:separator": r"\n------------------------------------\n",
            "prompt_formatter.0:field_name1": "context",
            "llm:wait_time": 0.5,
            "llm.0:output_type": "list",
            "llm.0:<UPDATE_STEP_TYPE>": "node_to_node",
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
            "llm.0:model_name": "chat_gpt4o_mini", 
            "llm.1:model_name": "chat_gpt4o_mini", 
            "summarizer:model_name": "groq",  
            "summarizer:prompt": prompt_summary, 
            "saver:output_folder": os.environ.get("OUTPUT_FOLDER"),
        }
        self.set_params(raw_params=params)


    def run(self, folder_path=None, prompt="", params={}, **kwargs):
        # Run method implementation...
````

## __post_init__ method
__post_init__ method has to be called before calling self.set_params method. It is because usually __post_init__ will be called automatically after __init__(you can check Closure.__init_subclass__), its main functionality is to rename all the Components assigned as self's attributes to attribute name themselves (e.g. self.x = Component() then this Component's base_name will be x instead of Component after calling __post_init__). If you want to use the new base_name (the attribute names) in self.set_params, you have to record them and call __post_init__ manually.

## Components and Execution Flow
1. **DirFileLister**
   - Scans the specified folder for text files
   - Output: List of file paths
   - Parameters:
     - `recursive`: Set to True for recursive file listing
     - `regex_pattern`: Set to `r".*\.txt$"` to match only .txt files
   - step_type = "node_to_list"

2. **TextExtractor**
   - Reads each file and extracts its content
   - Output: Raw text from input files
   - Parameters:
     - `word_limit`: Set to 1200 words
   - step_type = "node_to_node"

3. **Retriever**
   - Uses the input prompt to find the most relevant pieces of information based on embedding vectors
   - Output: Top k relevant text segments
   - Parameters:
     - `top_k`: Set to 3 to retrieve the top 3 relevant pieces of information
     - `query`: Set to the main input prompt
   - step_type = "list_to_list"

4. **Summarizer**
   - Condenses the retrieved text segments
   - Output: Short summaries (around 50 words) of extracted text
   - Parameters:
     - `model_name`: Set to "groq" for summarization
     - `prompt`: Uses a custom prompt to generate a 50-word paragraph summary
   - step_type = "node_to_node"

5. **TextCombiner**
   - Merges the summaries into a coherent text
   - Output: Combined summary text
   - Parameters:
     - `id_format`: Set to "<ID: {}>" for identifying each segment
     - `separator`: Set to a custom separator string
   - step_type = "list_to_node"

6. **PromptFormatter** (first instance)
   - Prepares the prompt for the LLM, incorporating the combined summary
   - Output: Formatted prompt string
   - Parameters:
     - `field_name1`: Set to "context"
     - `prompt`: Uses a custom prompt (prompt2) to identify relevant items for answering the main question
   - step_type = "node_to_node"

7. **LLMModel** (first instance)
   - Processes the formatted prompt using a language model
   - Output: Generated response based on the input
   - Parameters:
     - `wait_time`: Set to 0.5 seconds between LLM calls
     - `output_type`: Set to "list", so the output is a list of strings
     - `model_name`: Set to "chat_gpt4o_mini"
   - step_type = "node_to_node", there is one node whose content is a list

8. **Filter**
   - Purpose: Applies filtering
   - Output: Specific nodes that meet defined criteria
   - step_type = "list_to_list"   
   - Parameters and functionality:
     1. nodes:
        - Filtered using mql, e.g., {"step_name": {"$regex": "text_extractor", "$order": -1}}
        - "$order": -1 selects the last group of nodes with the matching step name
        - This step identifies the most recent "text_extractor" output in the pipeline

     2. filter_nodes:
        - Secondary set of nodes used as a reference for filtering "nodes"
        - Filtered similarly, e.g., {"step_name": {"$regex": "retriever", "$order": -1}}
        - Selects the last group of "retriever" nodes
        - There's a one-to-one relationship between nodes and filter_nodes. After filter the filter_nodes using filter_cri, the corresponding nodes are selected. Therefore filter_nodes are not the output, nodes are

     3. filter_cri:
        - criteria for filtering, often utilizing regular expressions
        - Can incorporate dynamic values through placeholders, e.g., {"node_id": {"$order": "[indices]"}}
        - [] is a operator for placeholder. Its value is get from the parameter with the same name to the Filter.run function.

     4. indices (this is an ad-hoc parameter for placeholder in filter_cri):
        - Defined in the input schema update, e.g., 
          ```json
          "indices": {
              "filter_cri": {"step_name": {"$regex": "llm.0"}},
              "dim": 0,
          }
          ```
        - Specifies how to extract the ordering information from LLM output
        - The LLM output (matching "llm.0" step) generates a list of integers
        - This list is used to determine selected nodes

   - Operational sequence:
     1. The component first identifies the last group of "text_extractor" nodes using the "nodes" parameter.
     2. It then identifies the last group of "retriever" nodes using the "filter_nodes" parameter.
     3. The "indices" parameter is used to extract ordering information from the most recent LLM output (the "llm.0" step).
     4. The "filter_cri" is applied according to "indices", using the LLM-generated index to select nodes.
     5. The filter_nodes are used to determine which of the main nodes are kept, but the output consists of the selected nodes, not the filter_nodes.

9. **PromptFormatter** (second instance)
   - Prepares the filtered output for final LLM processing
   - Output: Final formatted prompt
   - Parameters:
     - `field_name1`: Set to "context"
     - `prompt`: Uses a custom prompt (prompt3) incorporating the main question and filtered context
   - step_type = "node_to_node"

10. **LLMModel** (second instance)
    - answer the question formally taking into account the retrieved content.
    - Output: Final generated text
    - Parameters:
     - `model_name`: Set to "chat_gpt4o_mini"
    - step_type = "node_to_node"

11. **Saver**
    - Writes the final output to files
    - Parameters:
     - `output_folder`: Set to the value of `os.environ.get("OUTPUT_FOLDER")`
    - step_type = "node_to_node"

## Run Method

The `run` method is the main entry point for executing the pipeline:

````python
def run(self, folder_path=None, prompt="", params={}, **kwargs):
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
````

### Parameters:
- `folder_path`: Path to the folder containing txt files
- `prompt`: The main question or task for the pipeline to address
- `params`: Additional parameters to override defaults
- `**kwargs`: Additional keyword arguments

## Usage Example
```python
pipeline = RAG()
result = pipeline.run(
    folder_path="/path/to/pdf/files",
    prompt="What are the latest advancements in technology?, i am talking about physics",
)
```
