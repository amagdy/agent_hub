import os
import sys
import ollama

def test_ollama_connection():
    # 1. Read OLLAMA_HOST or fallback to the local default endpoint
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    print(f"📡 Target Endpoint: {ollama_host}")

    # 2. Instantiate the custom client with your environment's host
    client = ollama.Client(host=ollama_host)
    
    # Define a highly available, lightweight model to test with
    test_model = "granite4:3b" 

    print(f"🤖 Sending test chat message using model '{test_model}'...")
    
    try:
        # 3. Send a simple chat payload to the endpoint
        response = client.chat(
            model=test_model,
            messages=[
                {
                    "role": "user",
                    "content": "Respond with exactly the word 'SUCCESS' if you can read this.",
                }
            ]
        )
        
        # 4. Extract and print the response
        reply = response.message.content
        print("\n✅ Connection Verified!")
        print(f"Ollama Response: {reply.strip()}")

    except ollama.ResponseError as e:
        # Triggers if the server is alive, but something else went wrong (e.g., model not found)
        print(f"\n❌ Server responded with an error: {e.error}")
        if e.status_code == 404:
            print(f"💡 Suggestion: Run `ollama pull {test_model}` in your terminal first.")
            
    except Exception as e:
        # Triggers if the endpoint is completely unreachable (ConnectionRefusedError / httpx.ConnectError)
        print(f"\n❌ Could not connect to Ollama at {ollama_host}.")
        print(f"Error Details: {e}")
        print("💡 Suggestion: Verify that your Ollama app/service is running.")

if __name__ == "__main__":
    test_ollama_connection()

