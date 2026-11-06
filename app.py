
import uuid
import sqlite3
import streamlit as st

from pathlib import Path

from langchain_classic.chains import ConversationChain
from langchain_classic.memory import ConversationBufferMemory
from langchain_ollama import OllamaLLM


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="MindMate | Local AI",
    page_icon="🧠",
    layout="wide"
)

DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434"

DB_PATH = Path(__file__).parent / "mindmate.db"


# ==================================================
# 2. DATABASE CONNECTION
# ==================================================

def get_connection():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ==================================================
# 3. INITIALIZE DATABASE
# ==================================================

def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id)
            REFERENCES conversations(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ==================================================
# 4. CREATE NEW CONVERSATION
# ==================================================

def create_conversation():

    chat_id = str(uuid.uuid4())

    conn = get_connection()

    conn.execute("""
        INSERT INTO conversations (id, title)
        VALUES (?, ?)
    """, (chat_id, "New conversation"))

    conn.commit()
    conn.close()

    return chat_id


# ==================================================
# 5. GET ALL CONVERSATIONS
# ==================================================

def get_conversations():

    conn = get_connection()

    cursor = conn.execute("""
        SELECT id, title, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    """)

    conversations = [
        dict(row) for row in cursor.fetchall()
    ]

    conn.close()

    return conversations


# ==================================================
# 6. GET MESSAGES OF A CONVERSATION
# ==================================================

def get_messages(chat_id):

    conn = get_connection()

    cursor = conn.execute("""
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (chat_id,))

    messages = [
        dict(row) for row in cursor.fetchall()
    ]

    conn.close()

    return messages


# ==================================================
# 7. SAVE MESSAGES IN SQLITE
# ==================================================

def save_conversation(chat_id, prompt, answer):

    conn = get_connection()

    cursor = conn.cursor()

    # Save user message

    cursor.execute("""
        INSERT INTO messages (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
    """, (chat_id, "user", prompt))

    # Save assistant response

    cursor.execute("""
        INSERT INTO messages (
            conversation_id,
            role,
            content
        )
        VALUES (?, ?, ?)
    """, (chat_id, "assistant", answer))

    # Generate conversation title

    cursor.execute("""
        SELECT title
        FROM conversations
        WHERE id = ?
    """, (chat_id,))

    result = cursor.fetchone()

    if result and result["title"] == "New conversation":

        title = prompt.strip().replace("\n", " ")[:40]

        if len(prompt.strip()) > 40:
            title += "..."

        cursor.execute("""
            UPDATE conversations
            SET title = ?
            WHERE id = ?
        """, (title, chat_id))

    cursor.execute("""
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()


# ==================================================
# 8. CLEAR CONVERSATION
# ==================================================

def clear_conversation(chat_id):

    conn = get_connection()

    conn.execute("""
        DELETE FROM messages
        WHERE conversation_id = ?
    """, (chat_id,))

    conn.execute("""
        UPDATE conversations
        SET title = 'New conversation',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()


# ==================================================
# 9. INITIALIZE OLLAMA LLM
# ==================================================

@st.cache_resource
def load_llm():

    llm = OllamaLLM(
        model=DEFAULT_MODEL,
        base_url=OLLAMA_URL,
        temperature=0.7
    )

    return llm


# ==================================================
# 10. LOAD LANGCHAIN MEMORY
# ==================================================

def load_memory(chat_id):

    memory = ConversationBufferMemory(
        memory_key="history",
        input_key="input",
        return_messages=False
    )

    # Retrieve old messages from SQLite

    messages = get_messages(chat_id)

    # Load old messages into LangChain memory

    for message in messages:

        if message["role"] == "user":

            memory.chat_memory.add_user_message(
                message["content"]
            )

        elif message["role"] == "assistant":

            memory.chat_memory.add_ai_message(
                message["content"]
            )

    return memory


# ==================================================
# 11. SESSION STATE
# ==================================================

if "chat_id" not in st.session_state:

    st.session_state.chat_id = create_conversation()

if "memory" not in st.session_state:

    st.session_state.memory = load_memory(
        st.session_state.chat_id
    )


# ==================================================
# 12. CUSTOM CSS
# ==================================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        135deg,
        #0b1020,
        #111827 58%,
        #17152d
    );
    color: #ffffff;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp p,
.stApp label {
    color: #f8fafc;
}

[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #111827,
        #17152d
    );
    border-right: 1px solid #334155;
}

[data-testid="stSidebar"] * {
    color: #f8fafc !important;
}

.hero {
    padding: 28px;
    border: 1px solid #394267;
    border-radius: 22px;
    background: linear-gradient(
        120deg,
        #3730a355,
        #0ea5e933
    );
    margin-bottom: 20px;
}

.info {
    padding: 18px;
    border-radius: 14px;
    background: #1e293b;
    border: 1px solid #64748b66;
    margin-bottom: 10px;
    color: #f8fafc;
}

[data-testid="stChatMessage"] {
    border: 1px solid #64748b55;
    border-radius: 16px;
    background: #1e293b;
}

[data-testid="stChatMessage"] p {
    color: #ffffff !important;
}

[data-testid="stChatInput"] textarea {
    color: #ffffff !important;
    background: #1e293b !important;
    caret-color: white;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #cbd5e1 !important;
}

.stButton button {
    border-radius: 12px;
    border: 1px solid #818cf866;
    background: #4f46e533;
    color: white !important;
}

.stButton button:hover {
    background: #6366f1;
    border-color: #a5b4fc;
}

.stAlert p {
    color: white !important;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# 13. OLLAMA CONNECTION STATUS
# ==================================================

def ollama_is_running():

    try:

        import requests

        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=3
        )

        return response.ok

    except Exception:

        return False


# ==================================================
# 14. CONVERSATION CHAIN
# ==================================================

def ask_mindmate(prompt):

    # Load Ollama model

    llm = load_llm()

    # Use existing LangChain memory

    memory = st.session_state.memory

    # Create ConversationChain

    conversation_buf = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=False
    )

    # Generate response

    response = conversation_buf.predict(
        input=prompt
    )

    return response


# ==================================================
# 15. SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown("## 🧠 MindMate")

    st.caption("Your private local AI companion")

    st.divider()

    st.markdown("### 💬 Conversations")

    # New conversation button

    if st.button(
        "＋ New conversation",
        use_container_width=True
    ):

        new_chat_id = create_conversation()

        st.session_state.chat_id = new_chat_id

        st.session_state.memory = load_memory(
            new_chat_id
        )

        st.rerun()

    # Retrieve saved conversations

    conversations = get_conversations()

    chat_ids = [
        chat["id"] for chat in conversations
    ]

    chat_titles = {
        chat["id"]: chat["title"]
        for chat in conversations
    }

    # Conversation selector

    if chat_ids:

        current_index = (
            chat_ids.index(st.session_state.chat_id)
            if st.session_state.chat_id in chat_ids
            else 0
        )

        selected_chat = st.selectbox(
            "Previous conversations",
            options=chat_ids,
            index=current_index,
            format_func=lambda x: chat_titles[x]
        )

        if selected_chat != st.session_state.chat_id:

            st.session_state.chat_id = selected_chat

            st.session_state.memory = load_memory(
                selected_chat
            )

            st.rerun()

    st.divider()

    st.markdown("### 💾 Memory")

    st.markdown("""
    <div class="info">
        <b>ConversationBufferMemory</b><br>
        Retains conversation context.
        <br><br>
        <b>SQLite Database</b><br>
        Permanently stores previous chats.
    </div>
    """, unsafe_allow_html=True)

    # Clear conversation

    if st.button(
        "🗑 Clear conversation",
        use_container_width=True
    ):

        clear_conversation(
            st.session_state.chat_id
        )

        st.session_state.memory.clear()

        st.rerun()

    st.divider()

    st.caption("⚡ Powered by Ollama")

    st.caption(f"Model: {DEFAULT_MODEL}")

    st.caption("🔐 Local Database")


# ==================================================
# 16. MAIN HERO SECTION
# ==================================================

st.title("✨ Meet MindMate")

st.markdown(
    "Your personal AI companion that understands "
    "your conversation and remembers context."
)

st.markdown(
    "⚡ Ollama Powered  |  "
    "🧠 LangChain Memory  |  "
    "🔐 SQLite Storage"
)

st.divider()


# ==================================================
# 17. CONNECTION STATUS
# ==================================================

left, right = st.columns([1, 2])

with left:

    if ollama_is_running():

        st.success("Ollama is running")

    else:

        st.error("Ollama is not responding")

with right:

    st.info(f"AI Model: {DEFAULT_MODEL}")


# ==================================================
# 18. DISPLAY CHAT HISTORY
# ==================================================

messages = get_messages(
    st.session_state.chat_id
)

if not messages:

    st.markdown(
        "### 👋 Hello! What would you like to talk about?"
    )

    a, b, c = st.columns(3)

    with a:

        st.markdown("""
        <div class="info">
            💡 <b>Learn</b><br><br>
            Explain AI in simple words.
        </div>
        """, unsafe_allow_html=True)

    with b:

        st.markdown("""
        <div class="info">
            ✍️ <b>Create</b><br><br>
            Help me write an email.
        </div>
        """, unsafe_allow_html=True)

    with c:

        st.markdown("""
        <div class="info">
            🧩 <b>Explore</b><br><br>
            Suggest a Python project.
        </div>
        """, unsafe_allow_html=True)


# Display existing conversation

for message in messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ==================================================
# 19. CHAT INPUT
# ==================================================

prompt = st.chat_input("Message MindMate...")


if prompt:

    with st.chat_message("user"):

        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner("MindMate is thinking..."):

            try:

                # Generate answer using ConversationChain

                answer = ask_mindmate(prompt)

                st.markdown(answer)

                # Save both messages permanently

                save_conversation(
                    st.session_state.chat_id,
                    prompt,
                    answer
                )

            except Exception as exc:

                st.error(
                    f"Unable to generate response: {exc}"
                )

    # Refresh the interface

    st.rerun()
