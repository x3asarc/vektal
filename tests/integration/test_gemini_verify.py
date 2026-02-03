import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Try with the model ID we just set
    MODEL_ID = "gemini-2.5-flash"
    
    print(f"Testing model: {MODEL_ID}...")
    response = client.models.generate_content(
        model=MODEL_ID,
        contents="Hello, are you working?"
    )
    print(f"Success! Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
