# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 19:37:48 2024

@author: User
"""
# list of prompt:
# PROMPT_SUMMARY_WITH_TOPIC: context, topic

# context, target_language
# PROMPT_SUMMARIZE_AND_TRANSLATE_FOR_AUDIOBOOK = """
# You are tasked with creating an academic audiobook script. You will summarize or rewrite, translate, and explain the text provided, ensuring it is accessible for auditory learners who have no visual aids and may be new to the subject.

# ### Text to Summarize, Translate, and Explain:
# {context}

# ### Instructions:
# 1. Summarizing/rewrite the provided text, ensuring all essential information is included.
# 2. Translate into {target_language}. Present special nouns in both Chinese and English. For each specialized term, provide the {target_language} keywords followed by the English equivalent.
# 3. You dont need to add a new section for this, but clearly explain all the key academic ideas, words, principles and examples. You have to make sure that the students are not smart and no visual aids. Provide many details if needed
# 4. Please write in paragraphs so that you are planning to read the text to students. You need to write in sentences to describe/explain tables/formulas etc that are difficult to listen and understand
# 5. If it is quite clear that the content is not related to any meaningful issues (e.g. reference list, random words...) you can ignore such content
# 6. Do no write repeated ideas.
# 7. Do not write about who you are, what you need to do etc. Just do the task.

# ### Target Language:
# {target_language}
# """

PROMPT_SUMMARIZE_AND_TRANSLATE_FOR_AUDIOBOOK = """
You are tasked with creating an academic audiobook script for auditory learners. 
Your job is to summarize academic texts and explain the content clearly.

### Academic Text to Summarize and translate:
{context}

### Writing style and criteria:
0. Write your answer in text (assuming people cannot see it but can only listening to it). in other words, only punctuations and words. (e.g. x+y-> x plus y. also do not list your headings as #, but use numbers, e.g. firstly xx. secondly, yy). if possible, write organized sentences and paragraphs rather than phrases. 
1. Summarize the text to ensure inclusion of all essential information, ideas and examples.
2. Write in the target language: {target_language}. Include technical terms in both {target_language} and English, presenting them first in {target_language} followed by their English equivalent.
3. When explaining, assume the audience is unfamiliar with the subject and lacks visual aids.
4. Adapt descriptions for auditory presentation, especially when discussing complex visual content like tables or formulas. For example when explaining x=1, y=2, z=1+2, it is difficult to remember the numbers and symbols, so you should explain z as: z is equal to x plus y.
5. Omit irrelevant content, such as reference lists or extraneous information.
6. Avoid repetition of ideas.
7. Focus solely on the task; do not include personal introductions or explanations of the assignment.

### Essay format:
1. Introduction: (Briefly introduce the academic content as if presenting the topic to new learners)
2. Main Content: (Detailed paragraphs explaining key ideas and translating terms)
3. NO CONCLUSION

### Target Language:
{target_language}
"""

PROMPT_TRANSLATE = """
You are tasked with creating an academic audiobook script for auditory learners by translating academic texts.
Your job is to translate the provided academic content.

### Academic Text to Translate:
{context}

### Writing style and criteria:
0. Write your answer in text (assuming people cannot see it but can only listening to it). in other words, only punctuations and words. (e.g. x+y-> x plus y. also do not list your headings as #, but use numbers, e.g. firstly xx. secondly, yy). if possible, write organized sentences and paragraphs rather than phrases.
1. Ensure inclusion of all essential information, ideas and important examples.
2. Write in the target language: {target_language}. Include technical terms in both {target_language} and English, presenting them first in {target_language} followed by their English equivalent.
3. Adapt descriptions for auditory presentation, especially when discussing complex visual content like tables or formulas. For example when you want to explain x=1, y=2, z=1+2, it is difficult to remember the numbers and symbols, so you should explain it as: "z is equal to x plus y", notice to use words to describe formulas and try to use meaningful words instead of numbers for a best effort basis.
4. Do not include repeated ideas or content.
5. Focus solely on the task; avoid personal comments or unnecessary explanations.
6. Filter out any irrelevant content, such as reference lists or non-essential information.
7. DO NOT HALLUCINATE

### Target Language:
{target_language}
"""