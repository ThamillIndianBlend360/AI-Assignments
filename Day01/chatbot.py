import os
import ollama
from dotenv import load_dotenv

load_dotenv()

class OllamaChatbot:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        # Conversation history list for multi-turn support
        self.messages = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_response(self, user_input: str) -> str:
        # Append user question to history
        self.add_message("user", user_input)
        
        try:
            # Call Ollama API with full context history
            response = ollama.chat(
                model=self.model,
                messages=self.messages
            )
            bot_reply = response['message']['content']
            
            # Append assistant response to history
            self.add_message("assistant", bot_reply)
            return bot_reply
            
        except Exception as e:
            # Remove the last user message if API fails so history stays clean
            self.messages.pop()
            raise RuntimeError(f"Failed to communicate with Ollama: {e}")

    def clear_history(self):
        self.messages = []