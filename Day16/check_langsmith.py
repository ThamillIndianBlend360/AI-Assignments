from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

@traceable
def add(a: int, b: int) -> int:
    return a + b

if __name__ == "__main__":
    print("result:", add(2, 3))
