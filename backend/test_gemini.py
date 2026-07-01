import google.generativeai as genai
import os

api_key = "your_gemini_api_key_here"
genai.configure(api_key=api_key)

models_to_test = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-1.5-flash-latest"]

for m_name in models_to_test:
    print(f"Testing {m_name}...")
    try:
        model = genai.GenerativeModel(m_name)
        res = model.generate_content("hi")
        print(f"  SUCCESS: {res.text[:20]}")
    except Exception as e:
        print(f"  ERROR: {e}")
