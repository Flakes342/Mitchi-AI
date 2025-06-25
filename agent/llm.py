import re
from langchain_community.llms import Ollama
from typing import Optional, TypedDict
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda


SYSTEM_PROMPT_PATH = "agent/prompts/system_prompt.txt"
RAG_PROMPT_PATH = "agent/prompts/rag_prompt.txt"
CONEXT_SUMMARY_PROMPT_PATH = "agent/prompts/context_summary_prompt.txt"
TEXT_TO_SHELL_PROMPT_PATH = "agent/prompts/text_to_shell_prompt.txt"

llm = Ollama(model="gemma3:4b")

def load_system_prompt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()

system_prompt = load_system_prompt(SYSTEM_PROMPT_PATH)

def get_intent(user_input, clarify, reasoning, steps, final_instruction) -> dict:
    prompt = system_prompt + user_input + "\n\n" + \
             "### ADDITIONAL INFORMATION" + \
             f"Clarifications: {clarify}\n" + \
             f"Reasoning: {reasoning}\n\n"
            #  f"Steps: {', '.join(steps)}\n" + \
            #  f"Final Instruction: {final_instruction}\n\n"

    try:
        raw_response = llm.invoke(prompt).strip()
        json_block = re.sub(r"^```(?:json)?\n|\n```$", "", raw_response.strip(), flags=re.IGNORECASE) # Removing md block
        return json.loads(json_block)

    except Exception as e:
        print("[Intent parsing failed]", e)
        return {"function": "fallback", "args": {}, "error": str(e), "raw": raw_response}

# --- Prompt builder
def build_rag_prompt(user_input: str, memory_context_docs: list[str], about_context_docs: list[str]) -> str:
    memory_str = "\n".join(memory_context_docs)
    about_str = "\n".join(about_context_docs)
    return f"""
You are Mitchi, a concise and intelligent personal AI agent.

Here are the last few things you talked about:
{memory_str}

Furthermore, here is some additional context about the user:
{about_str}

Instruction:
Given the user input below, respond in a short, factual, and helpful way using the above context **only if it's relevant**. Do **NOT** guess or overexplain. DO **NOT** use direct sentences from the contexts, make it sound more natural. If no context applies, respond naturally and ask clarification questions.

User: "{user_input}"
""".strip()


def generate_context_summary(text: str):
    prompt = f"""
You are a Mitchi, a memory assistant.

Please generate a **short, high-quality contextual summary** of the user's message. The goal is to help retrieve this input later based on its intent, meaning, or relevance.

Focus on:
- The user’s **intent or fact stated** (e.g. they shared their name, asked a question, gave a command, made a preference known, etc.)
- Any **personal data** (like name, location, preferences)
- Any **task, question, or command** they gave
- Be **succinct, self-contained**, and only output the context.

Do **NOT** include generic statements like “The user said something” — instead be precise (e.g., “User shared their name is Ayush”).

Answer only with the cleaned-up, standalone context summary — no explanation, no prefixes.


Message: {text}
Summary:
"""
    summary = llm.invoke(prompt).strip()
    return None if summary.lower() == "none" else summary


def text_to_shell_command(message: str) -> str:
    prompt = f"""You are a Linux command generator.
Given a user's request in plain English, output the most appropriate shell command.
Only output the shell command, nothing else. Do **NOT** include any explanations or additional text.

User: {message}
Command:"""
    cmd = llm.invoke(prompt).strip()
    return cmd if cmd else "echo 'No command generated'"


def get_plan(user_input: str) -> dict:
    prompt = f"""
You are Mitchi's internal Planning Agent — a Chain-of-Thought thinker for pre-routing reasoning.

Your goal is to deeply analyze the user's natural language input and do the following:

---

### TASKS:

1. **Step-by-step reasoning:** Break down what the user likely wants, even if not fully explicit.
2. **Ask clarification**: ONLY IF there is ambiguity, return a clarification question in the `clarify` field.
3. **Decompose into steps**: List what needs to be done, in clean English steps.
4. **Generate the final instruction**: Rewrite the final command that should go to the intent router, with all ambiguities resolved.

---
### AVAILABLE TOOLS:
    1. open_app(name: str, query: Optional[str])
        Launch an application or open a specific search inside an app like YouTube or Spotify.
        If only an app name is given, omit query or set it to "".

    2. recommend_music()
        Only use this if the user explicitly asks for music suggestions, song recommendations, or similar.

    3. search_web(query: str)
        Use when the user asks to look something up online, e.g., "Google", "look up", "search web", "find info online".

    4. linux_commands(command: str)
        Use when the user asks to execute terminal commands (e.g., “run ls”, “show directory”).

    5. clock(type: str, hour: Optional[int], minute: Optional[int], seconds: Optional[int], objective: Optional[str])
        For alarms, timers, or current time.
        Types include: "alarm", "timer", "get_time", "get_active_alarms", "get_active_timers", "clear_alarms", "clear_timers".

    6. system_control(type: str, ...args)
        For system info, temperature, process handling, volume, shutdown, restart, etc.

    7. scraper_tool(url: str, output_format: Optional[str])
        Use this to scrape web pages for text or structured data. Dump the data in user asked format, if nothing is specified dump it as text. DO **NOT** use search_web when the user asks to scrape a URL.

    8. fallback()
        Use this if the user's message is:
            Conversational (e.g., “How are you?”, “This is cool”)
            Memory-based or personal (e.g., “What’s my name?”, “Remind me what I said”)
            Unclear, vague, or lacks a specific actionable intent
---

### EXAMPLES:

User: "my laptop is heating up"
→ 
{{
  "clarify": null,
  "reasoning": "The user is reporting a thermal issue. First, we need to check temperature. Then diagnose running processes. Possibly recommend tips.",
  "steps": [
    "Check system temperature",
    "List current running processes",
    "Suggest ways to reduce overheating"
  ],
  "final_instruction": "Check system temperature, list current processes, and suggest tips to reduce heating."
}}

User: "set a timer"
→ 
{{
  "clarify": "How long should I set the timer for?",
  "reasoning": "Timer duration is missing. Need more info before planning.",
  "steps": [],
  "final_instruction": ""
}}

User: "open Spotify and search for rainfall sounds"
→ 
{{
  "clarify": null,
  "reasoning": "User wants to launch Spotify and play a specific type of sound.",
  "steps": ["Open Spotify with the search term 'rainfall sounds'"],
  "final_instruction": "Open Spotify and search for rainfall sounds"
}}

User: "increase volume and check temperature"
→ 
{{
  "clarify": null,
  "reasoning": "This is a multi-function intent: increase volume and system health check.",
  "steps": ["Increase volume", "Check system temperature"],
  "final_instruction": "Increase volume and check system temperature"
}}

---

### USER INPUT:
\"\"\"{user_input}\"\"\"

Respond with a ***pure JSON*** object only:
{{
  "clarify": str or null,
  "reasoning": str,
  "steps": [list of steps],
  "final_instruction": str
}}
    """.strip()

    try:
        raw = llm.invoke(prompt).strip()
        json_block = raw.strip("` \n").replace("json\n", "")
        # print (json_block)
        return json.loads(json_block)
    
    except Exception as e:
        print("[get_llm_plan ERROR]", e)
        return {
            "clarify": None,
            "reasoning": "Fallback: could not parse plan.",
            "steps": [],
            "final_instruction": user_input
        }
    
def get_email_summary(date:str, sender: str,  subject:str, email_body: str) -> str:
    prompt = f"""You are Mitchi, a personal AI agent specializing in summarizing emails.
Your task is to generate a concise, high-quality summary of an email body.
Focus on:
- The main points or actions required
- Any important dates, names, or tasks mentioned
- Be succinct and self-contained, no need for explanations
- Do not include generic phrases like "The email says" — instead be precise (e.g "You need to attend the meeting on Friday at 10 AM")
Date: {date}
From: {sender}
Subject: {subject}
Email body: {email_body}
Summary:"""
    summary = llm.invoke(prompt).strip()
    return None if summary.lower() == "none" else summary


def write_email(subject: str, body: str, recipient: str) -> str: #-- Update functionality to fetch recipient from user input later
    prompt = f"""You are Mitchi, a personal AI assistant for Ayush Tanwar, responsible for drafting and sending well-crafted professional emails on his behalf.

Your task is to generate a concise, polished, and high-quality email using the subject and body provided by the user. The user will also provide the recipient's email address. Do not include the recipient’s email in the message body.

You must:
1. Start with a polite and appropriate greeting such as **"Hi [First Name],"** or **"Dear [Full Name],"** depending on the formality inferred from the subject/body. Extract the recipient's name from their email address if not explicitly mentioned. For example:
   - `john.doe@example.com` → "Hi John,"
   - `ceo@company.com` → "Dear Sir/Madam,"

2. Follow with a well-structured, clearly written email body that reflects Ayush’s voice: professional, respectful, and direct, yet warm when needed. Maintain a natural flow.

3. End with a professional closing:
   - Sign off as: **"Best regards,\nAyush Tanwar"**

4. Append the following disclaimer at the bottom:
   - **"Disclaimer: This email was written by Mitchi, Ayush's personal AI assistant."**

Now generate the email content based on the provided subject, body, and recipient.
Subject: {subject}
Body: {body}
Recipient: {recipient}
Format the output as a JSON object with the following structure:
{{
    "subject": "<Refined email subject>",
    "body": "<Fully formatted and finalized email body, including greeting, body, closing, and disclaimer>",
    "recipient": "{recipient}"
}}

DO **NOT** include any additional explanations or text outside the JSON object.
"""
    email_content = llm.invoke(prompt).strip()
    email_content_json = re.sub(r"^```(?:json)?\n|\n```$", "", email_content.strip(), flags=re.IGNORECASE) # Removing md block
    print("[write_email] Generated content:", email_content_json)
    return None if json.loads(email_content_json) == "none" else json.loads(email_content_json)