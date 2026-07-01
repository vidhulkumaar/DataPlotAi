import google.generativeai as genai
import os

api_key = "your_gemini_api_key_here"
genai.configure(api_key=api_key)

print("Listing models...")
models_to_test = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest"
]

print("Testing generation...")
for model_name in models_to_test:
    print(f"\n--- Testing {model_name} ---")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi, are you working?")
        print(f"Success! Response: {response.text[:50]}")
    except Exception as e:
        print(f"Error for {model_name}: {e}")
