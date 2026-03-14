import requests

def test_ollama():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("Ollama is running.")
            print("Models available:", response.json().get("models", []))
        else:
            print(f"Ollama returned status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to connect to Ollama: {e}")

if __name__ == "__main__":
    test_ollama()
