import google.generativeai as genai
import os

api_key = "your_gemini_api_key_here"
genai.configure(api_key=api_key)

print("Listing and testing models...")
try:
    models = genai.list_models()
    with open("model_test_report.txt", "w", encoding="utf-8") as f:
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name.split("/")[-1]
                f.write(f"Testing {m.name} (short: {model_name})...\n")
                try:
                    # Test only the ones that look like main models to save time/quota
                    if any(x in model_name for x in ["gemini-1.5", "gemini-2.0", "gemini-2.5", "flash", "pro"]):
                        model = genai.GenerativeModel(m.name)
                        response = model.generate_content("ping")
                        f.write(f"  SUCCESS: {response.text[:20]}...\n")
                    else:
                        f.write(f"  SKIPPED: unlikely candidate\n")
                except Exception as e:
                    f.write(f"  FAILED: {str(e)}\n\n")
    print("Done. Check model_test_report.txt")
except Exception as e:
    print(f"Error: {e}")
