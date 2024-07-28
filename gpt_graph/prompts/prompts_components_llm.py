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
