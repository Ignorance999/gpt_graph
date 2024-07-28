# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 19:37:48 2024

@author: User
"""
# list of prompt:
# PROMPT_SUMMARY_WITH_TOPIC: context, topic
# PROMPT_SMALL_OUTLINE: context
# PROMPT_OUTLINE: context
# PROMPT_SUMMARIZE: context
# PROMPT_TRANSLATION: target_language, context

# useful for all summarize and rewrite
PROMPT_CRITERIA = """
Identify and extract the key information, concepts, and details relevant to the chosen topic from the source text
Please focus on concrete examples, data, and factual information that provide in-depth insight into the topic.
Do not write anything not included in the source
Provide a thorough explanation of the main ideas, methodologies, or approaches discussed in the source material
Focus on the key aspects, components, or themes of the topic, such as important technologies, applications, concepts, or processes involved, and how they are utilized or implemented in practice
Ensure your response is COMPACT, CONCISE, COMPREHENSIVE, and INFORMATIVE, using phrases rather than complete sentences
Include as much relevant information as possible, especially special nouns and their functions
Avoid repeating ideas across sections
Disregard any information that is not directly related to the central theme or lacking depth or too general
"""

# doc: search_and_summarize, func: summarize_text, node_type: summary
#topic
PROMPT_SUMMARY_WITH_TOPIC = """
Summarize the following text, focusing on the topic: {topic}

`````text```
{context}
````````````

Guidelines:
You should focus on following elements:
""" + PROMPT_CRITERIA + """
Important: Please write your prompt in the most compact way possible. using phrases rather than complete sentences
If you meet an error or some unrelated text related to the topic, just return nothing
"""

#################################################################
# doc: rewrite, func: recursive_group_and_outline, node_type: top_summary/summary
#{context}
PROMPT_OUTLINE = """You are an expert planner. Create a concise, logical outline for rewriting the given text.

""" + PROMPT_CRITERIA + """
`````text```
{context}
`````````
Guidelines:

    Several sections with descriptive, parallel subtitles capturing main ideas
    Concise phrases, clear overview of content
    Avoid generic titles like "Introduction" or "Conclusion"
    Logical organization and coherent flow
    Similar section lengths
    General titles to allow sufficient content per section
    No information outside the provided text

Provide your outline adhering to these guidelines for effective rewriting.
"""


PROMPT_SMALL_OUTLINE = PROMPT_OUTLINE + "\n you should not write more than 100 words"


# doc: rewrite, func: summarize_sections, node_type: section_summary
PROMPT_SUMMARIZE = """You are a writer. You need to summarize the following into text. 
`````text```
{context}
`````
""" + PROMPT_CRITERIA + """    
you should include ALL the usefull information of the following text.
"""
#if you need quote, you should use the format: [SOURCE xxx] where xxx is number. you should not create new sources, you should just use the souce ID if provided

#target_language, context
PROMPT_TRANSLATION = """
Translate the following English text into {target_language}. 
`````text```
{context}
`````
If there are some key scientific language that is more suitable in english, you can still use them as english words.
Write your script in a way that is suitable for audiobook. In other words, assume that your listener does not have access to words but can only listen to them. In other words, you may need to write it in an essay form, but with concise language without much meaningless sentences
"""



