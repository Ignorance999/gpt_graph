# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 11:37:09 2024

@author: User
"""

import os
import sys
import logging
from typing import Type, List, Optional, Union
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from gpt_graph.utils.load_env import load_env

load_env()

from litellm import completion, batch_completion

# import instructor
from instructor import OpenAISchema
import litellm
import regex
import time
import json
import ast
import numpy as np
from jsonfinder import only_json
import inspect
import gpt_graph.prompts.prompts_components_llm as prompts
import time

try:
    from gpt_graph.components.llm_poe import LLM_POE
except:
    LLM_POE = None

from gpt_graph.core.component import Component
import tomli

# %% LLMModel


class LLMModel(Component):
    """
    1. Input Types and Their Implications
    variable: input_type/ self._input_type

    use _determine_input_type that categorizes input data into one of four types based on its structure:

    String ("string"): If the input is a plain string, it's treated as a single query or command.
    Message List ("message_list"): If the input is a list of dictionaries where each dictionary contains "role" and "content" keys, it's treated as a structured conversation log or series of instructions.
    Batch String ("batch_string"): If the input is a list of strings, each string is treated as a separate query or command to be processed in a batch.
    Batch Message ("batch_message"): If the input is a list of lists of dictionaries with "role" and "content" keys, each inner list is treated as a separate message thread or conversation to be processed in a batch.

    2. Output Types and Their Implications
    variable: output_type

    String ("string"): The model's response is expected to be a plain string.
    List ("list"): The model's response is expected to be a list of items, typically strings.
    JSON ("json")(only use this when using non-openai model): The model's response is expected to be a JSON string, which can be parsed into a Python dictionary or list.
    Boolean ("boolean"): The model's response is interpreted as a boolean value, true or false.

    There are 2 impacts of output_type to the model
    (1) a system message will be added at the beginning of the chat
    (2) the output will be parsed according to the type

    3. Formatting the Output:
    variable: self.model_nickname_map -> if_openai

    OpenAI Models:
        Utilize tooling and schemas for structured data output.
        Expect response to match the provided schema format.
        Extract content from tool_calls for parsing.
        For "list" output_type, retrieve "list_str" from the structured response.
        For "boolean" output_type, obtain the "value" from the structured response.

    Non-OpenAI Models:
        Depend on custom parsing logic for the output.
        For "boolean" output_type, apply regex to identify truthy or falsy statements in content.
        For "list" or "json" output_type, use regex to locate and ast.literal_eval to parse the largest bracketed text in the response into Python data structures.

    """

    step_type = ["node_to_node", "list_to_node", "list_to_list"]
    input_schema = {"input_data": {"type": str, "field": "content"}}
    cache_schema = {}
    output_schema = {"result": {"type": str}}
    output_format = "plain"

    def __init__(self, model_name=None, if_initialize_poe=False):
        super().__init__(if_auto_detect_input=True)
        # Initialize the different models with a nickname map and a boolean indicating if it's an OpenAI model
        # if __file__:  # TODO in formal version delete this
        gpt_graph_folder = os.getenv("GPT_GRAPH_FOLDER")

        if gpt_graph_folder is None:
            load_env()
            gpt_graph_folder = os.getenv("GPT_GRAPH_FOLDER")

        file_path = os.path.join(
            gpt_graph_folder,
            "config",
            "components",
            "llm_model_map.toml",
        )

        with open(file_path, "rb") as f:
            self.model_nickname_map = tomli.load(f)

        self.curr_model_name = model_name if model_name is not None else "test"
        self.current_model_info = self.model_nickname_map[self.curr_model_name]

        if if_initialize_poe:
            self.llm_poe = LLM_POE()
        if self.current_model_info.get("if_poe", False):
            self.llm_poe = LLM_POE(model_name=self.curr_model_name)
        else:
            self.llm_poe = None

    def chg_curr_model(self, model_name):
        self.curr_model_name = model_name if model_name is not None else "chat_mistral"
        self.current_model_info = self.model_nickname_map[self.curr_model_name]

    def add_model_nickname_map(self, updated_dict):
        self.model_nickname_map.update(updated_dict)

    def run(
        self,
        input_data: Union[str, List[Union[str, dict]]],
        output_type="string",  # list(both openai and not), json(only not openai), boolean(both openai and not)
        # dict(openai only), list_dict(openai only)
        output_example=None,
        tools=None,  # can be None/ openai_schema class def/ a dict containing class name and field/ a openai api dict for tool
        if_return_tool_name=False,
        model_name=None,
        max_fail_trials=2,
        output_schema=None,
        verbose=False,
        if_return_prompt=False,
        wait_time: float = 0,  # for batch input can use this
        # if_output_np = False,
        **kwargs,
        # batch_size: int = 5, for batch input can use this
    ) -> Union[str, list, dict]:
        output_type = output_type or "string"

        # Update current model if a new model name is provided
        if model_name is not None:
            self.curr_model_name = model_name
            self.current_model_info = self.model_nickname_map[self.curr_model_name]

        if model_name == "test":
            import uuid
            import random

            char_limit = 80

            def generate_test_output(output_type, input_data):
                if output_type == "string":
                    return (
                        f"{uuid.uuid1()}, The output is: {str(input_data)[:char_limit]}"
                    )
                elif output_type == "list":
                    return [str(uuid.uuid1()) for _ in range(random.randint(1, 5))]
                elif output_type == "json" or output_type == "dict":
                    return {
                        "id": str(uuid.uuid1()),
                        "content": str(input_data)[:char_limit],
                    }
                elif output_type == "boolean":
                    return random.choice([True, False])
                elif output_type == "list_dict":
                    return [
                        {"id": str(uuid.uuid1()), "content": str(input_data)[:50]}
                        for _ in range(random.randint(1, 3))
                    ]
                else:
                    return f"Unsupported output_type: {output_type}"

            output = generate_test_output(output_type, input_data)
            messages = [{"role": "user", "content": str(input_data)[:char_limit]}]
            if if_return_prompt:
                return output, messages
            else:
                return output

        if self.current_model_info.get("if_poe", False):
            output = self.run_poe(input_data)
            if if_return_prompt:
                return output, input_data
            else:
                return output

        if tools is not None and not self.current_model_info["if_openai"]:
            raise ValueError(
                f"Tools were provided but the selected model '{self.curr_model_name}' is not an OpenAI model. Please use output_schema instead"
            )

        input_type = self._determine_input_type(
            input_data
        )  # batch_string, message, or string, batch_message

        # Check if the model is OpenAI and if tools should be used
        if tools is None:
            class_schema = self._get_tools_if_needed(input_type, output_type)
        elif isinstance(tools, type) and issubclass(tools, OpenAISchema):
            class_schema = tools
        elif isinstance(tools, dict) and "class_name" in tools or "fields" in tools:
            class_schema = self._create_schema_class_from_spec(tools, output_type)
            # if output_type is list_dict will add a list layer outside the object
        elif isinstance(tools, list) and "function" in tools[0]:
            class_schema = None

        if class_schema is not None:
            tools = [{"type": "function", "function": class_schema.openai_schema}]

        messages = self._prepare_messages(
            input_data, input_type, output_type, output_example, output_schema, tools
        )

        self._input_type = input_type  # for debug
        self._messages = messages  # for debug
        self._tools = tools  # for debug
        self._class_schema = class_schema
        self._output_type = output_type
        if verbose:
            print("messages:", {j: k[:500] for i in messages for j, k in i.items()})

        attempt = 0
        if max_fail_trials > 0:
            if wait_time:
                time.sleep(wait_time)
            response = self._get_model_response(input_type, messages, tools, **kwargs)
            self._response_raw = response  # for debug
            try:
                # Parse and format the output
                if input_type in ("batch_message", "batch_string"):
                    output = []
                    for i in response:
                        output.append(
                            self._format_output(i, output_type, tools)
                        )  # ,if_output_np))
                else:
                    output = self._format_output(
                        response,
                        output_type,
                        tools,
                        if_return_tool_name=if_return_tool_name,
                    )  # , if_output_np)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                if attempt < max_fail_trials - 1:
                    print("Retrying...")
                    attempt += 1
                    output = self.run(
                        input_data=input_data,
                        output_type=output_type,
                        output_example=output_example,
                        model_name=model_name,
                        max_fail_trials=max_fail_trials - 1,
                        **kwargs,
                    )
                else:
                    print("Max retries reached. Returning last known response.")
                    output = response

        if if_return_prompt:
            return output, messages
        else:
            return output

    def run_poe(self, input_data):
        if self.llm_poe is None:
            self.llm_poe = LLM_POE()

        result = self.llm_poe.run(input_data)
        return result

    def _determine_input_type(self, input_data):
        if isinstance(input_data, str):
            return "string"
        elif isinstance(input_data, list):
            if all(
                isinstance(item, dict) and "role" in item and "content" in item
                for item in input_data
            ):
                return "message"
            elif all(isinstance(item, str) for item in input_data):
                return "batch_string"
            elif all(
                isinstance(item, list)
                and all(
                    isinstance(subitem, dict)
                    and "role" in subitem
                    and "content" in subitem
                    for subitem in item
                )
                for item in input_data
            ):
                return "batch_message"
            else:
                raise ValueError(
                    "List contains items with invalid or mixed structures."
                )
        else:
            raise ValueError("Invalid input data format.")

    def _prepare_messages(
        self,
        input_data,
        input_type,
        output_type=None,
        output_example=None,
        output_schema=None,
        tools=None,
    ):
        # Prepare the system message based on the output type
        system_message_type = None
        if tools is None:  # if have tools use tools first
            if output_type in ("json",):
                system_message_type = prompts.json_format_prompt
            elif output_type == "list":
                system_message_type = prompts.list_format_prompt
            elif output_type == "list_dict":
                system_message_type = prompts.list_dict_format_prompt
            elif output_type == "boolean":
                system_message_type = prompts.boolean_format_prompt
            elif output_type == "dict":
                system_message_type = prompts.dict_format_prompt

        # Initialize the prompt list with system messages if needed
        prompt_list = []
        if system_message_type is not None:
            prompt_list.append({"role": "user", "content": system_message_type})

        #         if tools is not None:
        #             prompt_list.append({"role":"system", "content":"""
        # Only use function/tool calling.
        # DO NOT RETURN ANYTHING except function calling
        # """})
        if output_schema is not None and output_type == "dict":
            output_example = (
                "{" + ",".join([f'"{i[0]}":"xx"' for i in output_schema]) + "}"
            )

        if output_example is not None:
            output_example_str = (
                "The output example is: "
                + output_example
                + "\nPlease follow strictly this format. "
            )
            prompt_list.append({"role": "user", "content": output_example_str})

        # Append the user input data to the prompt list
        if input_type == "string":
            prompt_list.append({"role": "user", "content": input_data})
        elif input_type == "message":
            # Assuming input_data is already a list of dicts with "role" and "content"
            prompt_list.extend(input_data)
        elif input_type == "batch_string":
            # Assuming each item in the batch should be treated as a separate message
            output = []
            for msg in input_data:
                prompt_list_temp = prompt_list.copy()
                prompt_list_temp.append({"role": "user", "content": msg})
                output.append(prompt_list_temp)
            prompt_list = output
        elif input_type == "batch_message":
            # Assuming each item in the batch should be treated as a separate message
            output = []
            for msg in input_data:
                prompt_list_temp = prompt_list.copy()
                prompt_list_temp.extend(msg)
                output.append(prompt_list_temp)
            prompt_list = output

        return prompt_list

    def _get_tools_if_needed(self, input_type: str, output_type: str):
        class ListStrSchema(OpenAISchema):
            """
            List of string
            """

            list_str: List[str] = Field(..., description="The string of a list")

        class BooleanSchema(OpenAISchema):
            """
            Boolean value
            """

            value: bool = Field(
                ..., description="A boolean value", examples=[True, False]
            )

        if self.current_model_info["if_openai"]:
            if input_type in ["string", "message"]:
                if output_type == "list":
                    return ListStrSchema  # [{"type": "function", "function": ListStrSchema.openai_schema}]
                elif output_type == "boolean":
                    return BooleanSchema  # [{"type": "function", "function": BooleanSchema.openai_schema}]
        return None

    def _get_model_response(
        self,
        input_type,
        messages,
        tools,
        batch_size: int = 5,
        wait_time: float = 1.0,
        **kwargs,
    ):
        # print(kwargs)
        # print(tools)
        target_params = inspect.signature(completion).parameters
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if key in target_params
        }
        max_tokens = self.current_model_info.get("max_tokens")
        if input_type in ("batch_string", "batch_message"):
            # Handle batch completion if a list of message lists is provided
            responses = []
            for i in range(0, len(messages), batch_size):
                batch_messages = messages[i : i + batch_size]
                responses.extend(
                    batch_completion(
                        model=self.current_model_info["model_id"],
                        messages=batch_messages,
                        tools=tools,
                        max_tokens=max_tokens,
                        **filtered_kwargs,
                    )
                )
                time.sleep(wait_time)
            return responses
        else:
            # Handle single completion
            return completion(
                model=self.current_model_info["model_id"],
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                **filtered_kwargs,
            )

    def _format_output(
        self,
        response,
        output_type,
        tools,
        if_return_tool_name=False,
        max_fail_trials=2,
        **kwargs,
    ):  # if_output_np,
        """
        Formats the output based on the output_type. Retries the model invocation if JSON parsing fails.
        """
        if tools:
            content = response["choices"][0]["message"]["tool_calls"][
                0
            ].function.arguments
        else:
            content = response["choices"][0]["message"]["content"]

        if output_type == "string":  # not in ["json", "list"]:
            output = content
        elif tools:  # using openai format
            output = json.loads(content)
            if output_type == "list":  # list of string
                output = output["list_str"]
            elif output_type == "boolean":
                output = output["value"]
            elif output_type == "list_dict":
                # output = output["list_of_items"]
                first_key = list(output.keys())[0]
                if len(output) == 1 and first_key.startswith("list_of_"):
                    # Return the value associated with the 'list_of_' key
                    output = output[first_key]
                else:
                    print("output type is not list dict")
                    output = output

            if if_return_tool_name:
                func_name = response["choices"][0]["message"]["tool_calls"][
                    0
                ].function.name
                output = {"name": func_name, "arguments": output}

        else:  # nonopenai format
            if output_type == "boolean":

                def parse_boolean_from_string(text):
                    true_pattern = regex.compile(
                        r"(?<=\W|^)(yes|true)(?=\W|$)", regex.IGNORECASE
                    )
                    false_pattern = regex.compile(
                        r"(?<=\W|^)(no|false)(?=\W|$)", regex.IGNORECASE
                    )

                    true_matches = true_pattern.search(text)
                    false_matches = false_pattern.search(text)

                    if true_matches and not false_matches:
                        return True
                    elif false_matches and not true_matches:
                        return False
                    else:
                        return None

                output = parse_boolean_from_string(content)
            elif output_type in ("list", "json", "dict", "list_dict"):
                output = only_json(content)[2]

        return output

    def _create_schema_class_from_spec(
        self, spec: dict, output_type="dict"
    ):  # or list_dict
        """
        Dynamically creates a Pydantic model class based on a specification.
        Used for tool schema creation

        Args:
        - spec: Dictionary with 'class_name' key and 'fields' key. 'fields' is a list of lists,
                where each inner list contains a field specification in the format [field_name, field_type].

        Returns:
        - Dynamically created class.

        example input:
            {
                "class_name": "DepartmentDes",
                "fields": [
                    ["department_name", str],
                    ["department_description", str]
                ]
            }
        """
        class_name = spec["class_name"]
        fields_spec = spec["fields"]

        # Prepare the attributes for the new class
        attributes = {
            "__annotations__": {},
            "__doc__": f"{class_name} with the following fields: {', '.join(f[0] for f in fields_spec)}",
        }

        # Process the fields specification
        for field_spec in fields_spec:
            if len(field_spec) == 2:
                field_name, field_type = field_spec
                attributes[field_name] = (
                    field_type,
                    Field(..., description=field_name),
                )
                attributes["__annotations__"][field_name] = field_type
            else:
                raise ValueError(
                    "Field specification must be a list with two elements: [field_name, field_type]"
                )

        # Create the new class using `type`
        new_class = type(class_name, (OpenAISchema,), attributes)

        if output_type == "list_dict":
            wrapper_class_name = f"List_{class_name}"
            wrapper_fields_spec = [["list_of_items", List[new_class]]]
            wrapper_spec = {
                "class_name": wrapper_class_name,
                "fields": wrapper_fields_spec,
            }
            # Recursively call the function to create the wrapper class with output_type='dict'
            return self._create_schema_class_from_spec(wrapper_spec, "dict")

        return new_class


# %%

if __name__ == "__main__":
    m = LLMModel(model_name="google")
    m = LLMModel(model_name="google_flash")
    # non openai model
    m = LLMModel(model_name="mistral")
    result = m.run("explain to me what is hello world")
    print(result)
    result = m.run("list 3 countries", output_type="list")
    print(result)
    result = m.run("do you like icecream?", output_type="boolean")
    print(result)
    result = m.run(["do you like ice", "do you like coke"], output_type="boolean")
    print(result)
    # input_type = batch_string
    result = m.run(["list 2 fruits", "list 2 dogs"], output_type="list")
    print(result)
    # input_type = batch_message
    result = m.run(
        [
            [{"role": "user", "content": "list 2 kinds of dogs"}],
            [{"role": "user", "content": "list 2 kinds of cats"}],
        ],
        output_type="list",
    )
    print(result)
    result = m.run(
        "name one industry and its merit",
        output_type="dict",
        output_schema=[["name", str], ["merit", str]],
    )
    print(result)

    result = m.run(
        "name 10 industries in real world and its merit",
        output_type="list_dict",
        output_schema=[["name", str], ["merit", str]],
    )
    print(result)
    # %%
    # openai model
    m2 = LLMModel(model_name="chat_gpt3")
    result = m2.run("explain to me what is hello world")
    print(result)
    result = m2.run("list 3 countries", output_type="list")
    print(result)
    result = m2.run("do you like icecream?", output_type="boolean")
    print(result)
    result = m2.run(["do you like ice", "do you like coke"], output_type="boolean")
    print(result)
    result = m2.run(["list 2 fruits", "list 2 kinds of dogs"], output_type="list")
    print(result)
    result = m2.run(
        [
            [{"role": "user", "content": "list 2 kinds of dogs"}],
            [{"role": "user", "content": "list 2 kinds of cats"}],
        ],
        output_type="list",
    )
    print(result)
    result = m2.run(
        "name an industry and its merits. simple answer. using function calling. DO NOT RETURN ANYTHING IN CONTENT ",
        output_type="dict",
        tools={"class_name": "industry", "fields": [["name", str], ["merit", str]]},
    )
    print(result)
    result = m2.run(
        "name 2 industries and its merits",
        output_type="list_dict",
        tools={"class_name": "industry", "fields": [["name", str], ["merit", str]]},
    )
    print(result)
    # %%
    m3 = LLMModel(model_name="groq_tool")
    result = m3.run("explain to me what is hello world")
    result = m3.run(["list 2 fruits", "list 2 kinds of dogs"], output_type="list")

    result = m3.run(
        "is apple contained in fruits? use tools",
        output_type="dict",
        tools={"class_name": "boolean", "fields": [["if_contain", bool]]},
    )

    print(result)
