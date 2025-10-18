# # src/test_env.py
# import os
# from dotenv import load_dotenv

# # Load .env from project root
# load_dotenv()

# key = os.getenv("OPENAI_API_KEY")
# if key:
#     print("✅ OPENAI_API_KEY detected in environment.")
#     print(f"Key starts with: {key[:10]}... (hidden for safety)")
# else:
#     print("❌ OPENAI_API_KEY not found.")
#     print("Make sure you have a .env file in your project root with a line like:")
#     print("OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx")

from dotenv import load_dotenv
load_dotenv()
import os
print("OPENAI_API_KEY present:", bool(os.getenv("OPENAI_API_KEY")))
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("OpenAI client created:", type(client))
except Exception as e:
    print("OpenAI client error:", e)