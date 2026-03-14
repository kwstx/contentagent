import json
import requests
import os

class LLMClient:
    def __init__(self, model="llama3", base_url="http://localhost:11434/api/generate"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, system_prompt=None):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(self.base_url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.Timeout:
            print(f"Error: LLM call timed out after 60 seconds.")
            return None
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None

    def query_json(self, prompt, system_prompt=None):
        """Helper to get JSON response from LLM."""
        json_prompt = prompt + "\n\nReturn the result as a raw JSON object string ONLY, with no markdown formatting or extra text."
        response_text = self.generate(json_prompt, system_prompt)
        if not response_text:
            return None
        
        try:
            # Clean possible markdown wrap
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            print(f"Failed to parse JSON from LLM: {e}")
            print(f"Raw response: {response_text}")
            return None
