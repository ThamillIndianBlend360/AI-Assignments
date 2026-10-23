import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")


def build_client():
    if not BASE_URL or not API_KEY or not MODEL:
        raise RuntimeError(
            "Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL."
        )

    return OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )


def call_llm(client, messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )

    return response.choices[0].message.content or ""


# -----------------------------------------------------
# VERSION A - DAY 1 BASELINE
# -----------------------------------------------------

def version_a(client, question):

    messages = [
        {
            "role": "user",
            "content": question
        }
    ]

    return call_llm(client, messages)


# -----------------------------------------------------
# VERSION B - IMPROVED INSTRUCTIONS
# -----------------------------------------------------

def version_b(client, question):

    # TODO:
    # Based on the failures you observed on Day 1,
    # decide what behavior you want from the assistant.
    #
    # Consider:
    # - What should the assistant do?
    # - What should it NOT do?
    # - What should happen when information is missing?
    # - What should happen when the request is ambiguous?

    system_instruction = """
You are a precise, reliable, and honest AI assistant. Follow these operational rules strictly:
1. Grounding & Truthfulness: Rely only on factual information. If you do not know an answer or if the information is missing, explicitly state "I do not know" or "This information is not provided" instead of fabricating details.
2. Ambiguity Handling: If a user prompt is vague, incomplete, or ambiguous, ask clarifying questions before attempting to answer.
3. Formatting: Structure your responses clearly using bullet points or concise paragraphs where appropriate.
"""

    messages = [
        {
            "role": "system",
            "content": system_instruction
        },
        {
            "role": "user",
            "content": question
        }
    ]

    return call_llm(client, messages)


# -----------------------------------------------------
# VERSION C - INSTRUCTIONS + RELEVANT CONTEXT
# -----------------------------------------------------

def version_c(client, question, context):

    # Use your Version B instruction here.
    system_instruction = """
You are a precise, reliable, and honest AI assistant. Follow these operational rules strictly:
1. Grounding & Truthfulness: Rely only on factual information. If you do not know an answer or if the information is missing, explicitly state "I do not know" or "This information is not provided" instead of fabricating details.
2. Ambiguity Handling: If a user prompt is vague, incomplete, or ambiguous, ask clarifying questions before attempting to answer.
3. Formatting: Structure your responses clearly using bullet points or concise paragraphs where appropriate.
"""

    user_message = f"""
Relevant information:

{context}

Question:
{question}
"""

    messages = [
        {
            "role": "system",
            "content": system_instruction
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    return call_llm(client, messages)


def main():

    client = build_client()

    question = input("Enter your test question: ")

    print("\n--- VERSION A ---")
    print(version_a(client, question))

    print("\n--- VERSION B ---")
    print(version_b(client, question))

    context = input(
        "\nEnter relevant context for Version C "
        "(leave blank if not required):\n"
    )

    print("\n--- VERSION C ---")
    print(version_c(client, question, context))


if __name__ == "__main__":
    main()