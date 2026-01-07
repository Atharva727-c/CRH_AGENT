#!/usr/bin/env python3
"""
Streamlit app for CRH Agent with chat interface and thinking UI
"""
import streamlit as st
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import snowflake.connector
from fpdf import FPDF
from pptx_generator import build_ppt_content, generate_ppt_bytes_cached
from pdf_generator import build_qa_pdf_payload, generate_qa_pdf_bytes_cached

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="CRH Agent",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Glassmorphism UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    /* ═══════════════════════════════════════════════════════════════
       GLASSMORPHISM / NEUMORPHISM MINIMALIST THEME
       ═══════════════════════════════════════════════════════════════ */

    /* Base app with gradient mesh background */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0f0f1a 100%);
        background-attachment: fixed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Subtle animated gradient orbs for depth */
    .stApp::before {
        content: '';
        position: fixed;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: 
            radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(72, 187, 255, 0.1) 0%, transparent 40%);
        pointer-events: none;
        z-index: 0;
    }

    /* Main content stays above background + WIDER layout */
    .main .block-container {
        position: relative;
        z-index: 1;
        max-width: 1400px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       TYPOGRAPHY - Larger font sizes
       ───────────────────────────────────────────────────────────────── */
    html, body, .stApp {
        font-size: 17px !important;
    }

    /* Headings */
    h1 {
        font-size: 2.5rem !important;
    }

    h2 {
        font-size: 1.8rem !important;
    }

    /* Welcome screen heading (force-match app title size) */
    .welcome-heading {
        font-size: 2.5rem !important;
        font-weight: 500 !important;
        color: rgba(255, 255, 255, 0.95) !important;
        text-align: center !important;
        margin-bottom: 1.5rem !important;
        letter-spacing: -0.3px !important;
    }

    h3 {
        font-size: 1.4rem !important;
    }

    h4 {
        font-size: 1.15rem !important;
    }

    /* Paragraphs and general text */
    p, .stMarkdown p, li {
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }

    /* Chat message text */
    [data-testid="stChatMessage"] p {
        font-size: 1.1rem !important;
        line-height: 1.75 !important;
    }

    /* Make chat messages wider */
    [data-testid="stChatMessage"] {
        max-width: 100% !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       CHAT INPUT - Lifted above footer
       ───────────────────────────────────────────────────────────────── */
    [data-testid="stChatInput"] {
        bottom: 50px !important;
        padding-bottom: 0rem !important;
    }

    /* Glass-styled chat input */
    [data-testid="stChatInput"] > div {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    }

    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: rgba(255, 255, 255, 0.9) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1.05rem !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       FIXED FOOTER - Glass effect
       ───────────────────────────────────────────────────────────────── */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 44px;
        background: rgba(15, 15, 26, 0.8);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        color: rgba(255, 255, 255, 0.4);
        text-align: center;
        line-height: 44px;
        font-size: 0.9rem;
        font-weight: 300;
        letter-spacing: 0.5px;
        z-index: 1000;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* ─────────────────────────────────────────────────────────────────
       SIDEBAR - Frosted glass panel
       ───────────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: rgba(20, 20, 35, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       CHAT MESSAGES - Glass cards
       ───────────────────────────────────────────────────────────────── */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 
            0 4px 24px rgba(0, 0, 0, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stChatMessage"]:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        transform: translateY(-1px);
    }

    /* ─────────────────────────────────────────────────────────────────
       EXPANDERS - Glass panels for thinking/tools
       ───────────────────────────────────────────────────────────────── */
    .stExpander {
        background: rgba(255, 255, 255, 0.02) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    .stExpander > div:first-child {
        background: transparent !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }

    .stExpander label, .stExpander summary {
        color: rgba(255, 255, 255, 0.85) !important;
        font-weight: 500 !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.3px;
    }

    /* ─────────────────────────────────────────────────────────────────
       BUTTONS - Neumorphic glass style
       ───────────────────────────────────────────────────────────────── */
    /* Primary buttons - soft glow */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.2) 0%, rgba(74, 158, 255, 0.1) 100%) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        color: rgba(140, 200, 255, 1) !important;
        border: 1px solid rgba(74, 158, 255, 0.3) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
        letter-spacing: 0.3px;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 
            0 4px 15px rgba(74, 158, 255, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
        transition: all 0.25s ease !important;
    }

    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(74, 158, 255, 0.3) 0%, rgba(74, 158, 255, 0.15) 100%) !important;
        border-color: rgba(74, 158, 255, 0.5) !important;
        box-shadow: 
            0 6px 25px rgba(74, 158, 255, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        transform: translateY(-1px);
    }

    /* Secondary buttons - subtle glass */
    .stButton>button[kind="secondary"], .stButton>button:not([kind]) {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        color: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        font-weight: 400 !important;
        font-size: 1rem !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 
            0 2px 10px rgba(0, 0, 0, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
        transition: all 0.25s ease !important;
    }

    .stButton>button[kind="secondary"]:hover, .stButton>button:not([kind]):hover {
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.12) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        transform: translateY(-1px);
    }

    /* ─────────────────────────────────────────────────────────────────
       SOURCE LINKS - Subtle glow
       ───────────────────────────────────────────────────────────────── */
    .source-link {
        color: rgba(120, 180, 255, 0.85);
        text-decoration: none;
        display: inline-block;
        margin: 0.4rem 0;
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        transition: all 0.2s ease;
        font-weight: 400;
        font-size: 1rem;
    }

    .source-link:hover {
        color: rgba(140, 200, 255, 1);
        background: rgba(74, 158, 255, 0.1);
        text-decoration: none;
    }

    /* ─────────────────────────────────────────────────────────────────
       GLASS CARD - Reusable component
       ───────────────────────────────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 
            0 4px 24px rgba(0, 0, 0, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        background: rgba(255, 255, 255, 0.045);
        border-color: rgba(255, 255, 255, 0.1);
    }

    .glass-card h4 {
        margin: 0 0 0.6rem 0;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 500;
        font-size: 1.1rem;
        letter-spacing: 0.2px;
    }

    .glass-card p {
        margin: 0;
        color: rgba(255, 255, 255, 0.7);
        line-height: 1.75;
        font-size: 1.05rem;
    }

    .glass-card pre {
        background: rgba(0, 0, 0, 0.3);
        font-size: 0.95rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 0.75rem;
        margin-top: 0.75rem;
        overflow-x: auto;
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.7);
    }

    .glass-card .icon-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    .glass-card .icon-title span {
        font-size: 1.1rem;
        opacity: 0.8;
    }

    /* ─────────────────────────────────────────────────────────────────
       TITLE - Clean typography
       ───────────────────────────────────────────────────────────────── */
    h1 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.5px !important;
        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(200,220,255,0.8));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ─────────────────────────────────────────────────────────────────
       MARKDOWN TEXT
       ───────────────────────────────────────────────────────────────── */
    .stMarkdown {
        color: rgba(255, 255, 255, 0.8);
    }

    .stMarkdown strong {
        color: rgba(255, 255, 255, 0.95);
        font-weight: 600;
    }

    /* ─────────────────────────────────────────────────────────────────
       DOWNLOAD BUTTON - Glass style
       ───────────────────────────────────────────────────────────────── */
    .stDownloadButton>button {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: rgba(255, 255, 255, 0.8) !important;
        transition: all 0.25s ease !important;
    }

    .stDownloadButton>button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       CHECKBOX - Minimal style
       ───────────────────────────────────────────────────────────────── */
    .stCheckbox label {
        color: rgba(255, 255, 255, 0.7) !important;
        font-weight: 400 !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       INFO/SUCCESS/ERROR BOXES - Glass panels
       ───────────────────────────────────────────────────────────────── */
    .stAlert {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
    }

    /* ─────────────────────────────────────────────────────────────────
       SPINNER
       ───────────────────────────────────────────────────────────────── */
    .stSpinner > div {
        border-color: rgba(74, 158, 255, 0.3) !important;
        border-top-color: rgba(74, 158, 255, 0.8) !important;
    }

</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

if "snowflake_conn" not in st.session_state:
    st.session_state.snowflake_conn = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
    st.session_state.pdf_filename = None
    st.session_state.pdf_regenerate = True

# Used to immediately switch from welcome screen to chat layout before running the LLM
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Configuration
ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
USER = os.getenv('SNOWFLAKE_USER')
PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
AGENT_NAME = "CRH_AGENT"
PROCEDURE_NAME = "RUN_CORTEX_AGENT"

def connect_to_snowflake():
    """Connect to Snowflake"""
    try:
        if st.session_state.snowflake_conn is None:
            conn = snowflake.connector.connect(
                user=USER,
                password=PASSWORD,
                account=ACCOUNT,
                database=DATABASE,
                schema=SCHEMA,
                login_timeout=20
            )
            st.session_state.snowflake_conn = conn
        return st.session_state.snowflake_conn
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None

def parse_agent_response(response_text):
    """Parse the agent response text format and extract components"""
    try:
        # Handle both string and already parsed responses
        if isinstance(response_text, str):
            text = response_text
        else:
            text = str(response_text)
        
        thinking_steps = []
        tool_calls = []
        final_text = None
        sources = []
        
        # Extract thinking steps (🧠 [PLANNING]:)
        planning_pattern = r'🧠\s*\[PLANNING\]:\s*(.*?)(?=🧠\s*\[PLANNING\]:|🛠️\s*\[TOOL CALL\]:|🤖\s*\[FINAL ANSWER\]:|\*\*Sources:\*\*|$)'
        planning_matches = re.findall(planning_pattern, text, re.DOTALL)
        for match in planning_matches:
            thinking_content = match.strip()
            if thinking_content:
                thinking_steps.append({
                    "title": "Planning the next steps",
                    "description": thinking_content,
                    "content": thinking_content
                })
        
        # Extract tool calls (🛠️ [TOOL CALL]:)
        tool_call_pattern = r'🛠️\s*\[TOOL CALL\]:\s*(\w+)\s*\n\s*Input:\s*({.*?})'
        tool_call_matches = re.findall(tool_call_pattern, text, re.DOTALL)
        for tool_name, tool_input in tool_call_matches:
            try:
                # Try to parse the input as JSON
                input_data = json.loads(tool_input)
            except Exception:
                input_data = tool_input
            tool_calls.append({
                "tool": tool_name,
                "input": input_data
            })
        
        # Extract final answer (🤖 [FINAL ANSWER]:)
        final_answer_pattern = r'🤖\s*\[FINAL ANSWER\]:\s*(.*?)(?=\*\*Sources:\*\*|$)'
        final_answer_match = re.search(final_answer_pattern, text, re.DOTALL)
        if final_answer_match:
            final_text = final_answer_match.group(1).strip()
        
        # Extract sources (**Sources:**)
        sources_pattern = r'\*\*Sources:\*\*\s*\n(.*?)(?=🧠|🛠️|🤖|$)'
        sources_match = re.search(sources_pattern, text, re.DOTALL)
        if sources_match:
            sources_text = sources_match.group(1).strip()
            # Extract URLs (lines starting with -)
            url_pattern = r'-\s*(https?://[^\s\n]+)'
            source_urls = re.findall(url_pattern, sources_text)
            for url in source_urls:
                sources.append({
                    "url": url.strip(),
                    "title": url.strip()
                })
        
        # If no final answer found, try to get the last section before Sources
        if not final_text:
            # Try to find text after the last tool call or planning step
            parts = re.split(
                r'(🧠\s*\[PLANNING\]:|🛠️\s*\[TOOL CALL\]:|🤖\s*\[FINAL ANSWER\]:|\*\*Sources:\*\*)',
                text
            )
            if len(parts) > 1:
                # Get the last meaningful text section
                for i in range(len(parts) - 1, -1, -1):
                    part = parts[i]
                    if (part and not part.startswith('🧠') and
                            not part.startswith('🛠️') and
                            not part.startswith('🤖') and
                            not part.startswith('**')):
                        potential_answer = part.strip()
                        if potential_answer and len(potential_answer) > 20:
                            final_text = potential_answer
                            break
        
        # Fallback: if still no final text, use the whole response
        if not final_text:
            final_text = text
        
        return {
            "thinking_steps": thinking_steps,
            "tool_calls": tool_calls,
            "final_text": final_text,
            "sources": sources
        }
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        # Debug: show the raw response in error
        if st.session_state.get("debug_mode", False):
            st.text(str(response_text)[:2000])
        return {
            "thinking_steps": [],
            "tool_calls": [],
            "final_text": str(response_text),
            "sources": []
        }

def call_agent(prompt):
    """Call the Snowflake agent"""
    conn = connect_to_snowflake()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Escape single quotes in the prompt
        escaped_prompt = prompt.replace("'", "''")
        
        # Call the stored procedure
        call_query = f"CALL {DATABASE}.{SCHEMA}.{PROCEDURE_NAME}('{DATABASE}', '{SCHEMA}', '{AGENT_NAME}', '{escaped_prompt}')"
        
        cursor.execute(call_query)
        result = cursor.fetchone()
        
        if result:
            response = result[0] if isinstance(result, tuple) else result
            cursor.close()
            return response
        else:
            cursor.close()
            return None
    except Exception as e:
        st.error(f"Error calling agent: {e}")
        return None

def display_thinking_steps(thinking_steps):
    """Display thinking steps in an expandable section similar to Snowflake Intelligence"""
    if not thinking_steps:
        return
    
    # Create a custom expandable section with better styling
    with st.expander("🧠 Thinking steps", expanded=True):
        for step in thinking_steps:
            title = step.get('title', 'Planning the next steps')
            description = step.get('description', step.get('content', ''))
            
            # Only show if there's actual content
            if not description or description.strip() == "":
                continue
            
            # Create a glass card for each thinking step
            st.markdown(f"""
            <div class="glass-card">
                <div class="icon-title">
                    <span>⚙️</span>
                    <h4>{title}</h4>
                </div>
                <p>{description}</p>
            </div>
            """, unsafe_allow_html=True)

def display_tool_calls(tool_calls):
    """Display tool calls"""
    if not tool_calls:
        return
    
    with st.expander("🛠️ Tool Calls", expanded=False):
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "Unknown")
            tool_input = tool_call.get("input", {})
            
            st.markdown(f"""
            <div class="glass-card">
                <div class="icon-title">
                    <span>🔧</span>
                    <h4>{tool_name}</h4>
                </div>
                <p><strong>Input:</strong></p>
                <pre>{json.dumps(tool_input, indent=2)}</pre>
            </div>
            """, unsafe_allow_html=True)

def display_sources(sources):
    """Display source links"""
    if not sources:
        return
    
    st.markdown("**Sources:**")
    for source in sources:
        url = source.get("url", "")
        title = source.get("title", url)
        if url:
            st.markdown(f'<a href="{url}" target="_blank" class="source-link">🔗 {title}</a>', unsafe_allow_html=True)

def sanitize_text(text):
    """Remove or replace Unicode characters that aren't supported by basic fonts"""
    if not text:
        return ""
    
    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '•': '-',  # Bullet point
        '—': '-',  # Em dash
        '–': '-',  # En dash
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '…': '...',  # Ellipsis
        '€': 'EUR',  # Euro sign
        '£': 'GBP',  # Pound sign
        '¥': 'JPY',  # Yen sign
        '©': '(c)',  # Copyright
        '®': '(R)',  # Registered
        '™': '(TM)',  # Trademark
    }
    
    # Replace Unicode characters
    result = str(text)
    for unicode_char, ascii_char in replacements.items():
        result = result.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-ASCII characters that might cause issues
    # Keep only printable ASCII characters (32-126) and newlines/tabs
    cleaned = ""
    for char in result:
        if ord(char) < 128 or char in ['\n', '\t', '\r']:
            cleaned += char
        else:
            cleaned += '?'  # Replace with ? if not ASCII
    
    return cleaned

def generate_pdf(messages):
    """Generate PDF from conversation messages"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Add a page
    pdf.add_page()
    
    # Set font for title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "CRH Agent Conversation Report", ln=True, align="C")
    pdf.ln(5)
    
    # Add date/time
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(10)
    
    # Process each message
    for idx, message in enumerate(messages, 1):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        # User message
        if role == "user":
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(230, 230, 230)
            question_num = idx//2 + 1 if idx > 1 else 1
            pdf.cell(0, 8, sanitize_text(f"Question {question_num}:"), ln=True, fill=True)
            pdf.ln(2)
            pdf.set_font("Arial", "", 11)
            # Handle long text by splitting into multiple lines
            pdf.multi_cell(0, 6, sanitize_text(content))
            pdf.ln(5)
        
        # Assistant message
        elif role == "assistant":
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, "Agent Response:", ln=True, fill=True)
            pdf.ln(2)
            
            # Thinking steps
            if "thinking_steps" in message and message["thinking_steps"]:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "Thinking Steps:", ln=True)
                pdf.ln(2)
                pdf.set_font("Arial", "", 10)
                for step in message["thinking_steps"]:
                    title = step.get("title", "Planning the next steps")
                    description = step.get("description", step.get("content", ""))
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, sanitize_text(f"  - {title}"), ln=True)
                    pdf.set_font("Arial", "", 9)
                    pdf.multi_cell(0, 5, sanitize_text(f"    {description}"))
                    pdf.ln(2)
            
            # Tool calls
            if "tool_calls" in message and message["tool_calls"]:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "Tool Calls:", ln=True)
                pdf.ln(2)
                pdf.set_font("Arial", "", 10)
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call.get("tool", "Unknown")
                    tool_input = tool_call.get("input", {})
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, sanitize_text(f"  - {tool_name}"), ln=True)
                    pdf.set_font("Arial", "", 9)
                    input_str = json.dumps(tool_input, indent=2) if isinstance(tool_input, dict) else str(tool_input)
                    pdf.multi_cell(0, 5, sanitize_text(f"    Input: {input_str}"))
                    pdf.ln(2)
            
            # Final answer
            if content:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "Answer:", ln=True)
                pdf.ln(2)
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 6, sanitize_text(content))
                pdf.ln(3)
            
            # Sources
            if "sources" in message and message["sources"]:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, "Sources:", ln=True)
                pdf.ln(2)
                pdf.set_font("Arial", "", 10)
                for source in message["sources"]:
                    url = source.get("url", "")
                    title = source.get("title", url)
                    pdf.cell(0, 5, sanitize_text(f"  - {title}"), ln=True)
                    if url != title:
                        pdf.set_font("Arial", "I", 9)
                        pdf.cell(0, 4, sanitize_text(f"    {url}"), ln=True)
                        pdf.set_font("Arial", "", 10)
                pdf.ln(3)
            
            pdf.ln(5)
            # Add page break if not last message
            if idx < len(messages):
                pdf.add_page()
    
    # Return PDF as bytes
    # fpdf2 output method returns bytearray when dest='S'
    try:
        result = pdf.output(dest='S')
        # Convert bytearray to bytes if needed
        if isinstance(result, bytearray):
            return bytes(result)
        elif isinstance(result, bytes):
            return result
        elif isinstance(result, str):
            return result.encode('latin-1')
        else:
            return bytes(result)
    except Exception as e:
        # Fallback: try without dest parameter
        try:
            result = pdf.output()
            if isinstance(result, (bytes, bytearray)):
                return bytes(result)
            return str(result).encode('latin-1')
        except Exception as e2:
            raise Exception(f"PDF generation failed: {str(e)} / {str(e2)}")


# Main app
st.title("💬 CRH Agent Chat")

# Sidebar with CRH branding and utilities
with st.sidebar:
    # CRH Logo (smaller, similar to sample)
    st.image("CRH-Plc-Logo.png", width=70)

    # Connection button just under logo
    if st.button("Test Connection", type="primary", use_container_width=True):
        conn = connect_to_snowflake()
        if conn:
            st.success("✓ Connected to Snowflake")
        else:
            st.error("✗ Connection failed")

    # Debug mode toggle
    st.session_state.debug_mode = st.checkbox(
        "🐛 Debug Mode",
        value=st.session_state.get("debug_mode", False),
    )

    # Clear chat & PDF export controls
    if st.button("🗑️ Clear Chat", type="primary"):
        st.session_state.messages = []
        st.session_state.pdf_bytes = None
        st.session_state.pdf_regenerate = True
        # Safe to reset here (the welcome input widget isn't instantiated in this scope)
        st.session_state["welcome_input"] = ""
        st.rerun()
    
    st.markdown("---")
    st.caption("Model Used : Snowflake Cortex Agent")


# Helper function to process a user prompt

def process_user_prompt(prompt: str):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response placeholder
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Call the agent
            response_json = call_agent(prompt)

            if response_json:
                # Debug: show raw response if debug mode is on
                if st.session_state.get("debug_mode", False):
                    with st.expander("🔍 Debug: Raw Response"):
                        st.text(str(response_json)[:2000])
                        # Show parsed structure
                        parsed = parse_agent_response(response_json)
                        st.write("Parsed structure:")
                        st.json({
                            "thinking_steps_count": len(parsed["thinking_steps"]),
                            "tool_calls_count": len(parsed["tool_calls"]),
                            "has_final_text": bool(parsed["final_text"]),
                            "sources_count": len(parsed["sources"])
                        })

                # Parse the response
                parsed = parse_agent_response(response_json)

                # Display thinking steps FIRST (before the response)
                if parsed["thinking_steps"]:
                    display_thinking_steps(parsed["thinking_steps"])

                # Display tool calls
                if parsed["tool_calls"]:
                    display_tool_calls(parsed["tool_calls"])

                # Display the final text AFTER thinking steps and tool calls
                if parsed["final_text"]:
                    st.markdown(parsed["final_text"])
                else:
                    st.info("No text response found in the agent output.")

                # Display sources
                if parsed["sources"]:
                    display_sources(parsed["sources"])

                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": parsed["final_text"] or "No response text available",
                    "thinking_steps": parsed["thinking_steps"],
                    "tool_calls": parsed["tool_calls"],
                    "sources": parsed["sources"]
                })
                # Mark PDF for regeneration when new message is added
                st.session_state.pdf_regenerate = True
                st.session_state.pdf_bytes = None  # Clear old PDF to force regeneration
                # Force rerun to update sidebar with new PDF
                st.rerun()
            else:
                error_msg = "Failed to get response from the agent. Please check your connection and try again."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })


def process_pending_prompt(prompt: str):
    """Process an already-enqueued prompt (user message is already in history)."""
    # Display assistant response placeholder
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_json = call_agent(prompt)

            if response_json:
                # Debug: show raw response if debug mode is on
                if st.session_state.get("debug_mode", False):
                    with st.expander("🔍 Debug: Raw Response"):
                        st.text(str(response_json)[:2000])
                        parsed = parse_agent_response(response_json)
                        st.write("Parsed structure:")
                        st.json({
                            "thinking_steps_count": len(parsed["thinking_steps"]),
                            "tool_calls_count": len(parsed["tool_calls"]),
                            "has_final_text": bool(parsed["final_text"]),
                            "sources_count": len(parsed["sources"])
                        })

                parsed = parse_agent_response(response_json)

                if parsed["thinking_steps"]:
                    display_thinking_steps(parsed["thinking_steps"])

                if parsed["tool_calls"]:
                    display_tool_calls(parsed["tool_calls"])

                if parsed["final_text"]:
                    st.markdown(parsed["final_text"])
                else:
                    st.info("No text response found in the agent output.")

                if parsed["sources"]:
                    display_sources(parsed["sources"])

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": parsed["final_text"] or "No response text available",
                    "thinking_steps": parsed["thinking_steps"],
                    "tool_calls": parsed["tool_calls"],
                    "sources": parsed["sources"]
                })
                st.session_state.pdf_regenerate = True
                st.session_state.pdf_bytes = None
                st.rerun()
            else:
                error_msg = (
                    "Failed to get response from the agent. "
                    "Please check your connection and try again."
                )
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })


# Display chat history
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # For assistant messages, show thinking first, then content
        if message["role"] == "assistant":
            # Display thinking steps FIRST if available
            if "thinking_steps" in message and message["thinking_steps"]:
                display_thinking_steps(message["thinking_steps"])

            # Display tool calls if available
            if "tool_calls" in message and message["tool_calls"]:
                display_tool_calls(message["tool_calls"])

            # Then display the content
            st.markdown(message["content"])

            # Finally display sources
            if "sources" in message and message["sources"]:
                display_sources(message["sources"])

            # Download PPTX for this particular Q/A
            question = None
            if idx > 0 and st.session_state.messages[idx - 1].get("role") == "user":
                question = st.session_state.messages[idx - 1].get("content", "")
            ppt_title = (question or "CRH Agent Answer").strip()
            ppt_content = build_ppt_content(
                answer_text=message.get("content", ""),
                sources=message.get("sources", []),
            )
            ppt_bytes = generate_ppt_bytes_cached(
                title=ppt_title[:120],
                content=ppt_content,
            )
            col_pptx, col_pdf = st.columns([1, 1], gap="small")
            with col_pptx:
                st.download_button(
                    label="Download PPTX",
                    data=ppt_bytes,
                    file_name=f"crh_agent_answer_{idx//2 + 1}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    key=f"pptx_download_{idx}",
                )
            with col_pdf:
                qa_payload = build_qa_pdf_payload(
                    question=question or "",
                    answer_text=message.get("content", ""),
                    thinking_steps=message.get("thinking_steps", []),
                    tool_calls=message.get("tool_calls", []),
                    sources=message.get("sources", []),
                )
                qa_pdf_bytes = generate_qa_pdf_bytes_cached(
                    title=(ppt_title or "CRH Agent Answer")[:120],
                    payload_text=qa_payload,
                )
                st.download_button(
                    label="Download PDF",
                    data=qa_pdf_bytes,
                    file_name=f"crh_agent_answer_{idx//2 + 1}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"pdf_download_{idx}",
                )
        else:
            # For user messages, just show content
            st.markdown(message["content"])

# Sample questions
sample_questions = [
    "What is the latest stock price of CEMEX today?",
    "Compare revenue of CRH and Vulcan for Q3 2024",
    "What is Holcim's sustainability strategy?",
]

# ═══════════════════════════════════════════════════════════════════════════
# CLAUDE-STYLE UI: Centered input for first chat, bottom for ongoing chat
# ═══════════════════════════════════════════════════════════════════════════

if len(st.session_state.messages) == 0:
    # ─────────────────────────────────────────────────────────────────────
    # FIRST CHAT: Centered welcome screen (like Claude)
    # ─────────────────────────────────────────────────────────────────────
    
    # Hide chat input and style the welcome screen
    st.markdown(
        """<style>
        [data-testid='stChatInput'] { display: none !important; }
        .fixed-footer { opacity: 0.3; }
        
        /* ChatGPT-style centered input - EXTRA TALL + TRUE PILL
           NOTE: markdown wrappers don't wrap Streamlit widgets, so we target the
           welcome input by its aria-label instead.
        */
        div[data-testid='stTextInput']:has(input[aria-label='Message input']) > div {
            background: rgba(64, 65, 79, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 9999px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            height: 78px !important;
            padding: 0 0.6rem !important;
            display: flex !important;
            align-items: center !important;
        }
        input[aria-label='Message input'] {
            background: transparent !important;
            border: none !important;
            color: rgba(255, 255, 255, 0.95) !important;
            font-size: 1.2rem !important;
            padding: 0 1.6rem !important;
            height: 78px !important;
            line-height: 78px !important;
        }
        /* Hide Streamlit's "Press Enter to apply" hint for the welcome input */
        div[data-testid='stTextInput']:has(input[aria-label='Message input'])
            [data-testid='InputInstructions'] {
            display: none !important;
        }

        input[aria-label='Message input']::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
        }

        /* Arrow submit button (ChatGPT-style) */
        div[data-testid="stFormSubmitButton"] button {
            width: 78px !important;
            height: 78px !important;
            padding: 0 !important;
            border-radius: 9999px !important;
            background: rgba(255, 255, 255, 0.92) !important;
            color: rgba(20, 20, 28, 1) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.25) !important;
            font-size: 44px !important;
            font-weight: 700 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1 !important;
        }

        /* Force the arrow glyph to scale (Streamlit may render it inside <p>/<span>) */
        div[data-testid="stFormSubmitButton"] button * {
            font-size: 44px !important;
            line-height: 1 !important;
        }

        div[data-testid="stFormSubmitButton"] button p {
            margin: 0 !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background: rgba(255, 255, 255, 1) !important;
            transform: translateY(-1px);
        }
        
        /* Sample buttons - LARGER */
        .welcome-buttons .stButton > button {
            font-size: 0.95rem !important;
            padding: 0.65rem 1rem !important;
            border-radius: 20px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Spacer to push content to vertical center
    st.markdown("<div style='height: 28vh;'></div>", unsafe_allow_html=True)
    
    # Centered title (match CRH Agent Chat size)
    st.markdown(
        "<div class='welcome-heading'>What can I help with?</div>",
        unsafe_allow_html=True,
    )
    
    # Input in a centered container - WIDER
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.form("welcome_form", clear_on_submit=True):
            col_in, col_submit = st.columns([0.88, 0.12], gap="small")
            with col_in:
                st.text_input(
                    label="Message input",
                    placeholder="Ask anything",
                    key="welcome_input",
                    label_visibility="collapsed",
                )
            with col_submit:
                submitted = st.form_submit_button("↑", use_container_width=True)

        if submitted:
            prompt_text = (st.session_state.get("welcome_input") or "").strip()
            if prompt_text:
                st.session_state.messages.append(
                    {"role": "user", "content": prompt_text}
                )
                st.session_state.pending_prompt = prompt_text
                st.rerun()
        
        # Small spacer
        st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
        
        # Sample question buttons
        st.markdown("<div class='welcome-buttons'>", unsafe_allow_html=True)
        btn_cols = st.columns(3, gap="small")
        for idx, (btn_col, question) in enumerate(zip(btn_cols, sample_questions)):
            with btn_col:
                if st.button(
                    question,
                    key=f"sample_q_{idx}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.messages.append({"role": "user", "content": question})
                    st.session_state.pending_prompt = question
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # ─────────────────────────────────────────────────────────────────────
    # ONGOING CHAT: Normal bottom-pinned chat input
    # ─────────────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Enter a message..."):
        process_user_prompt(prompt)

    # If we have a pending prompt from the welcome screen, process it after the
    # bottom chat input has rendered so the UI switches immediately.
    if st.session_state.get("pending_prompt"):
        pending = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        process_pending_prompt(pending)

# Fixed footer
st.markdown(
    "<div class='fixed-footer'>CRH Agent Chat Interface</div>",
    unsafe_allow_html=True,
)
