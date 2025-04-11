import streamlit as st
from llama_connector import query_llama
from db_connector import get_db_schema, run_sql_query
from PIL import Image
import base64
from io import BytesIO
import re
from datetime import datetime, timedelta

# Utility: Convert image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Utility: Extract SQL from model response
def extract_sql_from_response(response):
    sql_match = re.search(r'```sql(.*?)```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP).*?;', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(0).strip()
    return response.strip()

# Set up logos and favicon
encoded_logo = image_to_base64("icons/plogo.png")  # Updated path
favicon_base64 = image_to_base64("icons/plogo.png")  # Updated path
brain_icon_base64 = image_to_base64("icons/brain.png")  # Updated path
triangle_base64 = image_to_base64("icons/triangle.png")
bot_icon_base64 = image_to_base64("icons/bot.png")
# Set page config
st.set_page_config(
    page_title="PinnAI - Chat to your database",
    layout="wide",
    page_icon=f"data:image/png;base64,{favicon_base64}"
)

# -------------------------- Custom CSS
st.markdown(f"""
<style>
.main-container {{
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1rem;
}}

button[title="Hide sidebar"], button[title="Show sidebar"] {{
    display: none;
}}

.user-container {{
    display: flex;
    justify-content: flex-end;
}}
.user-bubble {{
    border: 1px solid #ccc;
    border-radius: 16px;
    padding: 10px 16px;
    margin: 8px 0;
    max-width: 80%;
    word-wrap: break-word;
    font-family: Arial, sans-serif;
    background: none;
}}

section[data-testid="stSidebar"] * {{
    border: none !important;
    box-shadow: none !important;
}}

section[data-testid="stSidebar"] input[type="text"] {{
    border: 1px solid #ccc !important;
    border-radius: 4px !important;
    padding: 0.25rem 0.5rem !important;
}}
</style>
""", unsafe_allow_html=True)

# -------------------------- Header with logo
st.markdown(f"""
<div style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 24px; width: 100%;">
    <img src="data:image/png;base64,{encoded_logo}" width="36" />
    <h3 style="margin: 0;">Hello I'm PinnAI, how can I help?</h3>
</div>
""", unsafe_allow_html=True)

# -------------------------- Session State Init
if "schema" not in st.session_state:
    st.session_state.schema = get_db_schema()

if "saved_chats" not in st.session_state:
    st.session_state.saved_chats = []

if "active_chat" not in st.session_state:
    st.session_state.active_chat = {
        "history": [],
        "summary": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# -------------------------- Sidebar with New Chat and Search
st.sidebar.image("icons/pinnacle.png", width=300)  # Updated path
st.sidebar.markdown(f"""
<div style='display: flex; align-items: center; gap: 8px;'>
    <img src='data:image/png;base64,{bot_icon_base64}' width='20' />
    <h3 style='margin: 0;'>PinnAI DB CHAT</h3>
</div>
""", unsafe_allow_html=True)


col_new, col_search = st.sidebar.columns([1, 4])
with col_new:
    if st.button("➕", key="new_chat", help="New Chat"):
        if st.session_state.active_chat["history"]:
            if not st.session_state.active_chat["summary"]:
                for m in st.session_state.active_chat["history"]:
                    if m["role"] == "user":
                        st.session_state.active_chat["summary"] = m["message"].split('.')[0][:50] + "..."
                        break
            st.session_state.saved_chats.append(st.session_state.active_chat)

        st.session_state.active_chat = {
            "history": [],
            "summary": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

with col_search:
    search_term = st.text_input("Search", label_visibility="collapsed", placeholder="Search chats...")

# -------------------------- Chat Grouping by Date
def group_chats_by_date():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    groups = {"Today": [], "Yesterday": [], "Last Week": []}
    for i, chat in enumerate(st.session_state.saved_chats):
        ts = datetime.strptime(chat["timestamp"], "%Y-%m-%d %H:%M:%S").date()
        if ts == today:
            groups["Today"].append((i, chat))
        elif ts == yesterday:
            groups["Yesterday"].append((i, chat))
        elif last_week <= ts < yesterday:
            groups["Last Week"].append((i, chat))
    return groups

grouped_chats = group_chats_by_date()

for group_name, chats in grouped_chats.items():
    filtered_chats = [c for c in chats if search_term.lower() in c[1]["summary"].lower()]
    if filtered_chats:
        with st.sidebar.expander(group_name, expanded=True):
            for i, chat in filtered_chats:
                col1, col2 = st.columns([8, 1])
                with col1:
                    if st.button(chat["summary"], key=f"load_chat_{i}"):
                        # Save the active chat before switching to an old chat
                        if st.session_state.active_chat["history"]:
                            if not st.session_state.active_chat["summary"]:
                                for m in st.session_state.active_chat["history"]:
                                    if m["role"] == "user":
                                        st.session_state.active_chat["summary"] = m["message"].split('.')[0][:50] + "..."
                                        break
                            st.session_state.saved_chats.append(st.session_state.active_chat)
                        
                        # Switch to the old chat
                        st.session_state.active_chat = chat
                with col2:
                    if st.button("❌", key=f"delete_chat_{i}"):
                        st.session_state.saved_chats.pop(i)
                        st.rerun()

# -------------------------- Chat Input and LLaMA Response
user_input = st.chat_input("Ask a question to the database...")

if user_input:
    st.session_state.active_chat["history"].append({"role": "user", "message": user_input})
    if not st.session_state.active_chat["summary"]:
        st.session_state.active_chat["summary"] = user_input.split('.')[0][:50] + "..."

    prompt = f"""
    You are an expert SQL assistant. Given this database schema:
    {st.session_state.schema}

    Convert this natural language request to MSSQL:
    "{user_input}"

    Return ONLY the SQL query, nothing else. No explanations, no markdown formatting.
    """

    with st.spinner("Generating Answer..."):
        try:
            llama_response = query_llama(prompt)
            clean_sql = extract_sql_from_response(llama_response)

            st.session_state.active_chat["history"].append({
                "role": "llama",
                "message": clean_sql
            })

            with st.spinner("Querying database..."):
                df = run_sql_query(clean_sql)

                if df is not None:
                    if len(df) == 0:
                        guidance = """
                        <div><strong>🔍 No results found</strong><br><br>
                        Try being more specific with:<br>
                        • Brand names (e.g., "Dell")<br>
                        • Exact specs (e.g., "Ryzen 7")<br>
                        • Filters (e.g., "with 16GB RAM")<br><br>
                        Example: "Show me Dell laptops with Ryzen 7 CPUs and 16GB RAM"
                        </div>
                        """
                        st.session_state.active_chat["history"].append({
                            "role": "guidance",
                            "message": guidance
                        })
                    else:
                        st.session_state.active_chat["history"].append({
                            "role": "result",
                            "message": df
                        })

        except Exception as e:
            st.session_state.active_chat["history"].append({
                "role": "error",
                "message": f"Error: {str(e)}"
            })

# -------------------------- Render Chat History
st.markdown('<div class="main-container">', unsafe_allow_html=True)

for entry in st.session_state.active_chat["history"]:
    if entry["role"] == "user":
        st.markdown(f'<div class="user-container"><div class="user-bubble">{entry["message"]}</div></div>', unsafe_allow_html=True)
    elif entry["role"] == "llama":
        st.markdown(f"""
        <p style="display: flex; align-items: center; gap: 8px; margin-top: 1rem;">
            <img src="data:image/png;base64,{brain_icon_base64}" width="20" style="vertical-align: middle;">
            <strong>AI Response:</strong>
        </p>

        ```sql
        {entry["message"]}
        ```
        """, unsafe_allow_html=True)
    elif entry["role"] == "result":
        st.markdown('📊 **Query Results:**')
        st.dataframe(entry["message"])

        txt = entry["message"].to_string(index=False).encode("utf-8")
        excel_buffer = BytesIO()
        entry["message"].to_excel(excel_buffer, index=False, engine='xlsxwriter')
        excel_data = excel_buffer.getvalue()
        excel_base64 = base64.b64encode(excel_data).decode()

        st.markdown(f"""
        <div class="export-icons">
            <a download="query_result.txt" href="data:text/plain;base64,{base64.b64encode(txt).decode()}" class="export-icon" title="Export as TXT">📄</a>
            <a download="query_result.xlsx" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_base64}" class="export-icon" title="Export as Excel">📊</a>
        </div>
        """, unsafe_allow_html=True)
    elif entry["role"] == "error":
        st.markdown(f"""
        <p style="display: flex; align-items: center; gap: 8px; margin-top: 1rem;">
            <img src="data:image/png;base64,{triangle_base64}" width="20" style="vertical-align: middle;">
             {entry["message"]}
        </p>
        """, unsafe_allow_html=True)
    elif entry["role"] == "guidance":
        st.markdown(entry["message"], unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
