
tool_descriptions = "" #placeholder
task = "" #placeholder

rules = """
Write a Python script that shows the process to do the task. However you should ONLY follow the following rules. Please write a FULL PLAN. DO NOT USE ANY OTHER TOOLS OTHER THAN SPECIFIED.

1. If you need function call, you can ONLY call following tools. You should not write your own functions unless they dont use any external libraries.

Tools available:
{tool_descriptions}
you also have google() as tool

2. IMPORTANT: Your output should ONLY contain code. You should not include any other thing that may result in failure when running the python script. You should not add ``` or any similar symbol or comment without # which may result in python script running failure
3. You should not include the definition of these tools. You can just import and call them.
4. when using llm_ask, you should write your prompt(query) as detail as possible. you can mark which part is important. Please also write example in a concrete way. Do you use abstract words like technologies, but rather use actual tech you may want to see
5. you have to include import any libraries if needed. only pandas, numpy and standard libraries are allowed to import
"""

plan_prompt = """

The task is: {task}

{rules}

The following is an example of example_task and your example_script:
example_task:
Your task is to read the doc x and summarize 10 topics. After that, google the topics and summarize the google results and write them to file.

example_script:
import write_file, read_file,google_search, llm_ask

s = read_file(filename = "x")
l = llm_ask(query = f"Please summarize the following text and produce 10 topics related to it. Your output should be a list of 10 topics, with comma to seperate and square bracket outside. e.g. ['aa','bb','cc']", output_type = "list")

t = ""
for i in l:
	o = google_search(i, num_of_items = 10)
	o2 = llm_ask(query = f"please summarize the following into one paragraph: {{{{o}}}}", output_format = "str")
	t.append(o2 + "\n")
	
write_file("summary",t)
	
"""

plan = "" #placeholder
undefined_funcs = ""

continue_prompt = """
You have to define the undefined functions of your plan.

You have the following task: {task}
Your plan is in the following code: 
{plan}

Now after checking, there are the following functions that you haven't defined:
{undefined_funcs}

Now your task is to define the: {undefined_func}

{rules}

You should write python script that actually works.
You can only call functions of the following if you need. You can import numpy, pandas or other core python libraries:
{tool_descriptions}

The following is an example output:
import os

def get_folder_name(file_path):
    # Get the directory path of the file
    directory_path = os.path.dirname(file_path)
    
    # Extract the folder name
    folder_name = os.path.basename(directory_path)
   
    return folder_name

"""


quote_style = """double"""

json_format_prompt = """
Output must be a Python literal json: strings in double quotes, dictionaries with quoted keys, escape special chars, no extra spaces/newlines, booleans as True/False, no trailing commas, integers without leading zeroes, and None for nulls, ensuring compatibility with ast.literal_eval().
"""

list_format_prompt = """
Output Python lists. Enclose in [], comma-separated, quote strings using double quote symbol, no trailing commas or spaces, no text outside.
"""

dict_format_prompt = """
Output Python dict. Enclose in {}, comma-separated, quote strings using double quote symbol, no trailing commas or spaces, no text outside. both keys and values should be quoted
"""

list_dict_format_prompt = """
Output Python list of dicts. Enclose in [], comma-separated, quote strings using double quote symbol, no trailing commas or spaces, no text outside. Inside the list, there are many dicts. Both keys and values should be {quote_style}-quoted
"""

boolean_format_prompt ="""
Output as single boolean value either True or False, python style. DO NOT INCLUDE ANY OTHER TEXT OR INSTRUCTION
"""

terms = ""
specific_general_prompt = """
Given a list of filename and paths, try to extract proprietary nouns that are related to technology. Especially those nouns that are trademarked or represent distinct products, services, or companies. DO NOT EXTRACT NOUNS THAT ARE too GENERAL OR TOO SIMPLE. 'General' refers to nouns that are widely used in normal worlds that arae not trademarked.

For example:
- "Google Search" would be extracted because it refers to a particular search service provided by Google.
- "Database" would be classified as 'General' and not extracted because it is a common term used to describe an organized collection of data.

Another Example:
Example Q: Please extract specific nouns for the following terms. output as a list.
['base.py', 'convert_to_openai.py', 'ifttt.py', 'plugin.py', 'render.py', 'retriever.py', 'yahoo_finance_news.py', '__init__.py', 'ainetwork\\app.py', 'ainetwork\\base.py']

Example Response:
["openai","yahoo_finance","ainetwork","ifttt"]

explanation of the response(DO NOT EVER INCLUDE THIS PART IN YOUR RESPONSE, YOUR RESPONSE SHOULD BE A PURE LIST):
only ["openai","yahoo_finance","ainetwork"] are specific nouns. you should check nouns ignoring .py ["ifttt"] is extracted, because although it is not related to trademark, it is a quite specific word that is not widely used in society: IF This Then That

Your task is to extract specific nouns from the following text. output as a list. your output should be specific nouns without repetitive meaning:
{terms}
"""


specific_general_prompt2 = """
Given a list of technology-related nouns, classify each term as either 'Specific' or 'General'. 'Specific' refers to proprietary nouns that are trademarked or represent distinct products, services, or companies. 'General' refers to nouns that are widely used in the technology field to describe concepts, actions, or generic tools not tied to a single entity. 

For example:
- "Google Search" would be classified as 'Specific' because it refers to a particular search service provided by Google.
- "Database" would be classified as 'General' because it is a common term used to describe an organized collection of data.

Another Example:
Example Q: Please extract specific nouns for the following terms. output as a list.
['base.py', 'convert_to_openai.py', 'ifttt.py', 'plugin.py', 'render.py', 'retriever.py', 'yahoo_finance_news.py', '__init__.py', 'ainetwork\\app.py', 'ainetwork\\base.py']

Example Response:
["openai","yahoo_finance","ainetwork"]

explanation of the response(DO NOT EVER INCLUDE THIS PART IN YOUR RESPONSE, YOUR RESPONSE SHOULD BE A PURE LIST):
only ["openai","yahoo_finance","ainetwork"] are specific nouns. you should check nouns ignoring .py

Your task is to extract specific nouns from the following text. output as a list. your output should be specific nouns without repetitive meaning:
{terms}
"""