import os
import json
from typing import List
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


