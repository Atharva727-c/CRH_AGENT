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

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="CRH Agent",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .user-message {
        background-color: #262730;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #1e1e1e;
        margin-right: 20%;
    }
    .thinking-card {
        background-color: #1a1a1a;
        border: 1px solid #333;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stExpander {
        background-color: #1a1a1a;
        border: 1px solid #333;
    }
    .stExpander label {
        color: #ffffff;
        font-weight: 500;
    }
    .source-link {
        color: #4a9eff;
        text-decoration: none;
        display: block;
        margin: 0.25rem 0;
    }
    .source-link:hover {
        text-decoration: underline;
    }
    .stButton>button {
        background-color: #4a9eff;
        color: white;
        border: none;
        border-radius: 0.25rem;
    }
    .stButton>button:hover {
        background-color: #3a8eef;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "snowflake_conn" not in st.session_state:
    st.session_state.snowflake_conn = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
    st.session_state.pdf_filename = None
    st.session_state.pdf_regenerate = True

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
            
            # Create a card-like container for each thinking step
            st.markdown(f"""
            <div style="
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 16px;
                margin: 12px 0;
            ">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 18px; margin-right: 8px;">⚙️</span>
                    <h4 style="margin: 0; color: #ffffff; font-weight: 500;">{title}</h4>
                </div>
                <p style="margin: 8px 0 0 0; color: #cccccc; line-height: 1.6;">{description}</p>
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
            <div style="
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 16px;
                margin: 12px 0;
            ">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 18px; margin-right: 8px;">🔧</span>
                    <h4 style="margin: 0; color: #ffffff; font-weight: 500;">{tool_name}</h4>
                </div>
                <div style="color: #cccccc;">
                    <strong>Input:</strong>
                    <pre style="background-color: #0a0a0a; padding: 8px; border-radius: 4px; margin-top: 8px; overflow-x: auto;">{json.dumps(tool_input, indent=2)}</pre>
                </div>
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

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    st.info(f"**Database:** {DATABASE}\n\n**Schema:** {SCHEMA}\n\n**Agent:** {AGENT_NAME}")
    
    # Debug mode toggle
    st.session_state.debug_mode = st.checkbox("🐛 Debug Mode", value=st.session_state.get("debug_mode", False))
    
    if st.button("🔌 Test Connection"):
        conn = connect_to_snowflake()
        if conn:
            st.success("✓ Connected to Snowflake")
        else:
            st.error("✗ Connection failed")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.pdf_bytes = None
        st.session_state.pdf_regenerate = True
        st.rerun()
    
    # Download PDF button - show when there are messages
    st.markdown("---")
    
    # Check if there are messages
    has_messages = len(st.session_state.messages) > 0
    
    if has_messages:
        st.markdown("### 📥 Export Conversation")
        
        # Debug info (only in debug mode)
        if st.session_state.get("debug_mode", False):
            st.write(f"Messages: {len(st.session_state.messages)}")
            st.write(f"Has PDF: {st.session_state.get('pdf_bytes') is not None}")
            st.write(f"Regenerate flag: {st.session_state.get('pdf_regenerate', False)}")
        
        # Generate PDF if needed (always check, not just in debug mode)
        should_generate = (
            st.session_state.get("pdf_regenerate", True) or
            st.session_state.get("pdf_bytes") is None
        )
        
        if should_generate:
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = generate_pdf(st.session_state.messages)
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.pdf_filename = (
                        f"crh_agent_conversation_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    st.session_state.pdf_regenerate = False
                    # Don't show success message - it's automatic
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"PDF generation failed: {error_msg}")
                    if st.session_state.get("debug_mode", False):
                        st.exception(e)
                    st.session_state.pdf_bytes = None
        
        # Always show download button if PDF exists
        if st.session_state.get("pdf_bytes"):
            st.download_button(
                label="📥 Download PDF Report",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.get(
                    "pdf_filename",
                    "crh_agent_conversation.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
                key="pdf_download_button"
            )
        else:
            # Show regenerate button if PDF generation failed
            if st.button("🔄 Regenerate PDF", use_container_width=True, key="regenerate_pdf"):
                st.session_state.pdf_regenerate = True
                st.session_state.pdf_bytes = None
                st.rerun()
    else:
        st.info("💡 Start a conversation to export as PDF")

# Display chat history
for message in st.session_state.messages:
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
        else:
            # For user messages, just show content
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question..."):
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

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>CRH Agent Chat Interface</div>",
    unsafe_allow_html=True
)

