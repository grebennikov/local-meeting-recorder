import sys
import socket
import psutil
import subprocess
from openai import OpenAI

interface = "wlp194s0"

def get_ip_address(interface_name):
    addresses = psutil.net_if_addrs()

    if interface_name not in addresses:
        return f"Interface '{interface_name}' not found."

    for snicattr in addresses[interface_name]:
        # Filter for IPv4 addresses
        if snicattr.family == socket.AF_INET:
            return snicattr.address

    return f"No IPv4 address assigned to '{interface_name}'."

model_url = "http://%s:13305/api/v1" % get_ip_address(interface)


# Point client to your local server
client = OpenAI(
    base_url=model_url,  # Change port depending on your server
    api_key="ollama"                       # Any non-empty string works locally
)


# 1. Read the local file


file_content = sys.stdin.read()
#file_path = "/tmp/transcript.txt"
#with open(file_path, "r", encoding="utf-8") as file:
#    file_content = file.read()

query_input = sys.argv[1]

with open(query_input, "r") as query_file:
    query =  query_file.read()

#query_pw_create = f"""Summarize the content of the provided transcript of the conversation. Assume multiple participants."
#query_pw_create = f"""You are a secretary in a technical company that is asked to summarize the the content of the provided \
#        transcript of the conversation. Assume multiple participants. Make sure to capture the timestamp in the beginning of \
#        the transcript and make a specific line in the beginning of the summary when it is generated. Include date and time in the format of MM-DD-YYYY HH:MM:SS"

query_pw_create = f"""{query}\

--- ATTACHED FILE: transcript ---
{file_content}
--- END ATTACHED FILE ---
"""

#
#--- ATTACHED FILE: {file_path} ---
#{file_content}
#--- END ATTACHED FILE ---
#"""

#print (query_pw_create)

response = client.chat.completions.create(
    model="gemma4-it-e4b-FLM",
#    model="qwen3.5-4b-FLM",
#    model="Gemma-4-E4B-it-GGUF",
    messages=[
        {"role": "system", "content": "You are a secretary in the IT company capturing technical meeting."},
        {"role": "user", "content": query_pw_create}
#        {"role": "user", "content": "aaa"}
    ],
    temperature=0.3
#    temperature=0.7
)

print(response.choices[0].message.content)
