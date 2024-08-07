# GPT Graph

GPT Graph is a flexible library designed to address some of the limitations of LangChain, particularly its over-abstraction. While it's still in early development and not yet sophisticated, it aims to offer features for component creation, pipeline orchestration, and dynamic caching. Its main advantage is that it can be debugged easily, with every output stored in a node for easy inspection.

Please note that this project is subject to change and is currently targeted at fast prototyping for small projects. It does not use a database at the moment. 

## Project link
Project link: [gpt_graph](https://github.com/Ignorance999/gpt_graph)

## Features

- Component-based architecture for modular design
- Basic pipeline orchestration
- Simple dynamic caching
- Conditional execution of components
- Easy Debugging and graphic analysis tools(using pyvis)

## How to study this project
It is recommended to start with all the tutorials. Then you can study the webpage structure and debug_tips

## Installation

As this package is in an early stage of development, it is highly recommended to install it using a virtual environment.

1. Create and activate a virtual environment
2. Install the package in editable mode:
   ```
   pip install -e .
   ```
3. Verify the installation:
   ```
   pip show gpt_graph
   ```
4. Modify parameters
If you want to run any Components/Pipelines, you may need to set parameter files for them. 
You may need to set the following in advance.

gpt_graph/config/config.toml # indicate which parameter file Components/Pipelines are using
gpt_graph/config/env.toml # you need to set GPT_GRAPH_FOLDER as the GPT_GRAPH's installation folder. you may also need to set other folders.

## Hello World Example

Here's a simple example to get you started:

```python
from gpt_graph.core.pipeline import Pipeline
from gpt_graph.core.decorators.component import component

@component()
def greet(x):
    return x + " world!"

pipeline = Pipeline()
pipeline | greet()

result = pipeline.run(input_data="Hello")
print(result)
```

Output:
```
['Hello world!']
```

