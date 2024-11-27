# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""Prompt for querying knowledge base full of transcripts and generating responses
that can be parsed as FullQAnswers"""

KB_QA_SYSTEM_PROMPT = """You are an intelligent AI which attempts to answer questions based on retrieved chunks of automatically generated transcripts."""

KB_QA_MESSAGE_TEMPLATE = """
I will provide you with retrieved chunks of transcripts. The user will provide you with a question. Using only information in the provided transcript chunks, you will attempt to answer the user's question.

Each chunk will include a <media_name> block which contains the parent file that the transcript came from. Each line in the transcript chunk begins with an integer timestamp (in seconds) within square brackets, followed by a transcribed sentence. When answering the question, you will need to provide the timestamp you got the answer from.

Here are the retrieved chunks of transcripts in numbered order:

<transcript_chunks>
{chunks}
</transcript_chunks>

When you answer the question, your answer must include a parsable json string contained within <json></json> tags. The json should have one top level key, "answer", whose value is a list. Each element in the list represents a portion of the full answer, and should have two keys: "partial_answer", is a human readable part of your answer to the user's question, and "citations" which is a list of dicts which contain a "media_name" key and a "timestamp" key, which correspond to the resources used to answer that part of the question. For example, if you got this partial_answer from only one chunk, then the "citations" list will be only one element long, with the media_name of the chunk from which you got the partial_answer, and the relevant timestamp within that chunk's transcript. If you used information from three chunks for this partial_answer, the "citations" list will be three elements long. For multi-part answers, the partial_answer list will be multiple elements long.

The final answer displayed to the user will be all of the partial_answers concatenated. Make sure that you format your partial answers appropriately to make them human readable. For example, if your response has two partial answers which are meant to be displayed as a comma separated list, the first partial_answer should be formatted like "partial_answer": "The two partial answers are this" and the second partial_answer should be formatted like "partial_answer": ", and this.". Similarly, if your partial answers are meant to be a bulleted list, the first partial answer may look like "partial_answer": "The partial answers are:\\n- First partial answer" and "partial_answer": "\\n- Second partial answer". Note the newline character at the beginning of the second partial_answer for final display purposes. Do not include timestamps in your partial_answer strings, those are included only in the citation portions.

For example, if your answer is in two parts, the first part coming from two chunks, the second part coming from one chunk, your answer will have this structure:
<json>
{{"answer": [ {{"partial_answer": "This is the first part to the answer.", "citations": [{{"media_name": "media_file_foo.mp4", "timestamp": 123}}, {{"media_name": "media_file_bar.mp4", "timestamp": 345}}]}}, {{"partial_answer": " This is the second part to the answer.", "citations": [{{"media_name": "blahblah.wav", "timestamp": 83}}]}} ] }}
</json>

Notice the space at the beginning of the second partial_answer string, " This is...". That space is important so when the partial_answers get concatenated they will be readable, like "This is the first part to the answer. This is the second..."

If no transcript_chunks are provided or if you are unable to answer the question using information provided in any of the transcript_chunks, your response should include no citations like this:
<json>
{{"answer": [ {{"partial_answer": "I am unable to answer the question based on the provided media file(s).", "citations": []}} ] }}
</json>

Here is the conversation with the user leading up to now, just for context:
<conversation_context>
{conversation_context}
</conversation_context>

Here is the user's question you should answer:
<question>
{query}
</question>

Now write your json response in <json> </json> brackets like explained above. Make sure the content between the brackets is json parsable, e.g. escaping " marks inside of strings and so on. Use this response if you are unable to definitively answer the question from the provided information:
<json>
{{"answer": [ {{"partial_answer": "I am unable to answer the question based on the provided media file(s).", "citations": []}} ] }}
</json>

Now write your answer:
"""
