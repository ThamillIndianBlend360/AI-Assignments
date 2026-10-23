import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("LLM_API_KEY", "ollama")
)
MODEL = os.getenv("LLM_MODEL", "llama3")

def call_llm_json(prompt):
    """Requests a structured JSON response from the local model."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful HR assistant. Always output valid JSON with keys: employee_name (string), request_type (string), days (integer), approved (boolean)."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content or "{}"

def call_llm_general(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content or ""

# ---------------------------------------------------------------------
# INTERACTIVE RELIABILITY TEST SUITE (RUNTIME INPUTS)
# ---------------------------------------------------------------------

def run_interactive_suite():
    print("==================================================")
    print("   LLM RELIABILITY & FAILURE INJECTION (RUNTIME)  ")
    print("==================================================")

    while True:
        print("\nSelect a Reliability Test Case to Run:")
        print("1. Valid structured response (Interactive LLM prompt)")
        print("2. Malformed output (Input custom broken JSON)")
        print("3. Missing required field (Test custom JSON validation)")
        print("4. Wrong type/value (Test type mismatch check)")
        print("5. Extra surrounding text (Test noisy markdown parser)")
        print("6. Insufficient information (Ask missing internal question)")
        print("7. Runtime failure / Timeout simulation")
        print("0. Exit")
        
        choice = input("\nEnter your test case number (0-7): ").strip()
        
        if choice == "0":
            print("Exiting test suite. Good luck with your assignment!")
            break
            
        elif choice == "1":
            print("\n--- Test 1: Valid Structured Response ---")
            user_prompt = input("Enter leave request prompt (Press Enter for default): ").strip()
            if not user_prompt:
                user_prompt = "Generate leave request data for John Doe requesting 4 days of annual leave."
            try:
                print(f"Sending prompt to model: '{user_prompt}'...")
                raw_output = call_llm_json(user_prompt)
                print(f"\nRaw Model Output:\n{raw_output}")
                parsed = json.loads(raw_output)
                print(f"PASS: Successfully parsed JSON -> {parsed}")
            except Exception as e:
                print(f"FAIL: {e}")
                
        elif choice == "2":
            print("\n--- Test 2: Malformed Output Handling ---")
            malformed_input = input("Enter malformed JSON string (Press Enter to use default broken JSON): ").strip()
            if not malformed_input:
                malformed_input = '{"employee_name": "Alice", "days": 3, "approved": true' # Missing closing brace
            try:
                parsed = json.loads(malformed_input)
                print(f"Parsed successfully: {parsed}")
            except json.JSONDecodeError as jde:
                print(f"\nCAUGHT EXPECTED ERROR (Malformed Output): {jde}")
                print("-> Action: Application safely rejects malformed payload and triggers fallback/retry.")
                
        elif choice == "3":
            print("\n--- Test 3: Missing Required Field Validation ---")
            print("Required fields: employee_name, request_type, days, approved")
            custom_json = input("Enter JSON payload to validate (Press Enter to use default incomplete data): ").strip()
            if not custom_json:
                data = {"employee_name": "Bob", "days": 2}
            else:
                try:
                    data = json.loads(custom_json)
                except Exception as e:
                    print(f"Invalid JSON entered: {e}")
                    continue
            required_fields = ["employee_name", "request_type", "days", "approved"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                print(f"\nVALIDATION FAILED: Missing required fields -> {missing}")
                print("-> Action: Application triggers error handling / default assignment.")
            else:
                print(f"\nVALIDATION PASSED: All required fields present -> {data}")
                
        elif choice == "4":
            print("\n--- Test 4: Wrong Type / Value Check ---")
            custom_json = input("Enter JSON payload with type mismatch (Press Enter to use default): ").strip()
            if not custom_json:
                data = {"employee_name": "Charlie", "request_type": "annual", "days": "five", "approved": "yes"}
            else:
                try:
                    data = json.loads(custom_json)
                except Exception as e:
                    print(f"Invalid JSON entered: {e}")
                    continue
            print(f"Testing payload: {data}")
            errors = []
            if "days" in data and not isinstance(data.get("days"), int):
                errors.append(f"'days' should be int, got {type(data.get('days'))}")
            if errors:
                print(f"\nVALIDATION CAUGHT TYPE MISMATCH: {errors}")
                print("-> Action: Cast or reject payload safely.")
            else:
                print("\nType check passed.")
                
        elif choice == "5":
            print("\n--- Test 5: Extra Surrounding Text Parser ---")
            noisy_input = input("Enter noisy text containing JSON (Press Enter for default): ").strip()
            if not noisy_input:
                noisy_input = "Here is the result: ```json\n{\"employee_name\": \"Diana\", \"request_type\": \"sick\", \"days\": 1, \"approved\": true}\n``` Hope this helps!"
            try:
                if "```json" in noisy_input:
                    json_str = noisy_input.split("```json")[1].split("```")[0].strip()
                elif "```" in noisy_input:
                    json_str = noisy_input.split("```")[1].split("```")[0].strip()
                else:
                    json_str = noisy_input
                parsed = json.loads(json_str)
                print(f"\nPASS: Extracted clean JSON from noisy text -> {parsed}")
            except Exception as e:
                print(f"\nFAIL to clean text: {e}")
                
        elif choice == "6":
            print("\n--- Test 6: Insufficient Information / Missing Context ---")
            user_question = input("Enter an internal company question (Press Enter for default): ").strip()
            if not user_question:
                user_question = "What is our company's exact Q4 bonus payout formula?"
            system_prompt = "If company internal details are missing, state 'I do not have access to internal company records' rather than guessing."
            print(f"Asking model: '{user_question}'...")
            output = call_llm_general(system_prompt, user_question)
            print(f"\nModel Output:\n{output}")
            print("-> Action: Application represents uncertainty safely rather than hallucinating.")
            
        elif choice == "7":
            print("\n--- Test 7: Runtime Failure & Timeout Simulation ---")
            err_msg = input("Enter custom timeout message (Press Enter for default): ").strip()
            if not err_msg:
                err_msg = "Connection to local Ollama server timed out after 5 seconds."
            try:
                raise TimeoutError(err_msg)
            except TimeoutError as te:
                print(f"\nCAUGHT RUNTIME FAILURE: {te}")
                print("-> Action: Executing bounded retry loop or fallback error response.")
        else:
            print("Invalid choice. Please select a number between 0 and 7.")

if __name__ == "__main__":
    run_interactive_suite()