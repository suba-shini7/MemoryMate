MINDMATE - LOCAL AI CHATBOT WITH MEMORY

1. Install Ollama: https://ollama.com/
2. Open Command Prompt and run:
   ollama pull qwen2.5:3b
3. Open this folder in VS Code.
4. In the VS Code terminal, run:
   pip install -r requirements.txt
5. Start the app:
   streamlit run app.py

Ollama should be running at http://localhost:11434.
SQLite stores chat messages in chat_memory.db.
The latest 12 messages are sent as context to the model.

Optional model:
   ollama pull llama3.2:3b
Then select it in the sidebar.
