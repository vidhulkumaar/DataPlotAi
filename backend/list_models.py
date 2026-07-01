import google.generativeai as genai
import os
import sys

api_key = "your_gemini_api_key_here"
genai.configure(api_key=api_key)

try:
    for m in genai.list_models():
        print(f"Name: {m.name}, Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
