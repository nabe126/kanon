import os
import sys

print("=== AI Agent Container Initialized ===")
print(f"Python Version: {sys.version}")
print(f"API Key Configured: {'Yes' if os.getenv('GEMINI_API_KEY') != 'your_key_here' else 'No (Default)'}")
print("=======================================")
