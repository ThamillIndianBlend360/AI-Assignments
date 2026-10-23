from chatbot import OllamaChatbot

def main():
    bot = OllamaChatbot()
    print("=" * 50)
    print(f"🤖 Ollama Multi-Turn Chatbot (Model: {bot.model})")
    print("Type your questions below. Type 'exit' or 'quit' to stop.")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye!")
                break
                
            if user_input.lower() == "clear":
                bot.clear_history()
                print("\n[Conversation history cleared!]\n")
                continue

            print("Bot is thinking...", end="\r")
            reply = bot.get_response(user_input)
            print(" " * 20, end="\r")
            print(f"Bot: {reply}\n")

        except KeyboardInterrupt:
            print("\n\nSession interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n[Error]: {e}\nMake sure Ollama is running locally!\n")

if __name__ == "__main__":
    main()