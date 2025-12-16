# CRH Agent

A personalized AI agent for CRH (Cement Roadstone Holdings) that leverages Snowflake Cortex Agent to provide intelligent insights about CRH's business operations, including projects, financials, safety, supply chain, and equipment data.

## Overview

The CRH Agent is an intelligent conversational interface that allows users to query CRH's business data using natural language. It connects to Snowflake's Cortex Agent framework to process queries and provide detailed responses with thinking steps, tool calls, and source citations.

## Features

- **Natural Language Querying**: Ask questions about CRH's business data in plain English
- **Interactive Web Interface**: Beautiful Streamlit-based chat interface with dark theme
- **Transparent AI Reasoning**: View the agent's thinking steps and tool calls
- **Source Citations**: All responses include source links for verification
- **PDF Export**: Export conversation reports as PDF documents
- **Database Integration**: Direct connection to Snowflake data warehouse

## Project Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Streamlit Web Application (streamlit_app.py)  │  │
│  │  - Chat Interface                                     │  │
│  │  - Response Parsing & Display                         │  │
│  │  - PDF Generation                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Application Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Agent Test Script (agent.py)                  │  │
│  │  - Snowflake Connection                               │  │
│  │  - Stored Procedure Execution                         │  │
│  │  - Response Logging                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Response Parser (extract_final_text.py)           │  │
│  │  - Parse Agent Responses                              │  │
│  │  - Extract Thinking Steps                            │  │
│  │  - Extract Tool Calls                                │  │
│  │  - Extract Sources                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Data Layer                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Snowflake Cortex Agent                        │  │
│  │  - RUN_CORTEX_AGENT Stored Procedure                 │  │
│  │  - Natural Language Processing                       │  │
│  │  - Query Planning & Execution                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         CRH Database Schema                           │  │
│  │  - Projects, Financials, Safety                        │  │
│  │  - Supply Chain, Equipment                            │  │
│  │  - Defined in CHR_DB_Realtion.yaml                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. **streamlit_app.py** - Web Application
The main user interface built with Streamlit that provides:
- **Chat Interface**: Interactive conversation UI with message history
- **Response Parsing**: Extracts and displays thinking steps, tool calls, and final answers
- **Visual Components**: 
  - Thinking steps displayed in expandable cards
  - Tool calls with formatted JSON input
  - Source links with clickable URLs
- **PDF Export**: Generates comprehensive PDF reports of conversations
- **Connection Management**: Handles Snowflake connections with session state

**Key Functions:**
- `connect_to_snowflake()`: Establishes and manages Snowflake connections
- `call_agent(prompt)`: Executes the Cortex Agent stored procedure
- `parse_agent_response(response_text)`: Parses structured agent responses
- `generate_pdf(messages)`: Creates PDF reports from conversation history

#### 2. **agent.py** - Agent Test Script
Command-line script for testing the Snowflake Cortex Agent:
- Connects to Snowflake using environment variables
- Calls the `RUN_CORTEX_AGENT` stored procedure
- Logs responses to `agent_procedure_results.txt`
- Handles multiple procedure name variants
- Provides detailed error messages and debugging information

**Usage:**
```bash
python agent.py
```

#### 3. **extract_final_text.py** - Response Parser
Utility script for parsing agent responses from log files:
- Extracts thinking steps (🧠 [PLANNING]: sections)
- Extracts tool calls (🛠️ [TOOL CALL]: sections)
- Extracts final answers (🤖 [FINAL ANSWER]: sections)
- Extracts source URLs (**Sources:** sections)
- Outputs structured JSON and text files

**Output Files:**
- `agent_parsed_response.json`: Structured JSON with all components
- `agent_final_response.txt`: Plain text final answer

#### 4. **CHR_DB_Realtion.yaml** - Database Schema Definition
YAML configuration file defining the CRH database schema:
- **Tables**: 8 core business tables
  - `CLIENTS`: Client profiles and relationships
  - `PROJECTS`: Project details and management
  - `PROJECT_FINANCIALS`: Financial metrics by quarter
  - `COMPETITOR_FINANCIALS`: Competitor analysis data
  - `SAFETY_INCIDENTS`: Workplace safety records
  - `EQUIPMENT_INVENTORY`: Equipment assets and status
  - `MATERIALS_CATALOG`: Material catalog and suppliers
  - `MATERIAL_USAGE_LOG`: Material consumption tracking
  - `SUBCONTRACTORS`: Subcontractor information
- **Relationships**: Defines foreign key relationships between tables
- **Dimensions & Facts**: Specifies dimensional modeling structure

### Data Flow

1. **User Query** → User enters question in Streamlit interface
2. **Connection** → Application connects to Snowflake (cached in session)
3. **Procedure Call** → Executes `RUN_CORTEX_AGENT` stored procedure with:
   - Database name
   - Schema name
   - Agent name (`CRH_AGENT`)
   - User query
4. **Agent Processing** → Snowflake Cortex Agent:
   - Analyzes the query
   - Plans execution steps
   - Calls appropriate tools (database queries, web search, etc.)
   - Generates structured response
5. **Response Parsing** → Application parses response into:
   - Thinking steps
   - Tool calls
   - Final answer
   - Sources
6. **Display** → UI displays parsed components in organized format
7. **Export** → User can export conversation as PDF

### Technology Stack

- **Python 3.x**: Core programming language
- **Streamlit**: Web application framework
- **Snowflake Connector**: Database connectivity
- **Snowflake Cortex Agent**: AI agent framework
- **FPDF2**: PDF generation library
- **python-dotenv**: Environment variable management
- **YAML**: Configuration file format

## Installation

### Prerequisites

- Python 3.8 or higher
- Snowflake account with Cortex Agent access
- Access to CRH database in Snowflake

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Atharva727-c/CRH_AGENT.git
   cd CRH_AGENT
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   ```

4. **Verify Snowflake setup:**
   - Ensure the `RUN_CORTEX_AGENT` stored procedure exists
   - Verify the `CRH_AGENT` is configured in Snowflake
   - Confirm access to the CRH database schema

## Usage

### Web Interface

Start the Streamlit application:
```bash
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

**Features:**
- Enter questions in the chat input
- View thinking steps and tool calls
- Click source links to verify information
- Download conversation as PDF
- Clear chat history
- Test Snowflake connection

### Command Line Testing

Test the agent directly:
```bash
python agent.py
```

This will:
- Connect to Snowflake
- Execute a test query
- Save results to `agent_procedure_results.txt`

### Response Parsing

Parse agent responses from log files:
```bash
python extract_final_text.py
```

This reads `agent_procedure_results.txt` and generates:
- `agent_parsed_response.json`: Structured data
- `agent_final_response.txt`: Plain text answer

## Project Structure

```
CRH_Agent/
│
├── streamlit_app.py          # Main Streamlit web application
├── agent.py                  # Agent test script
├── extract_final_text.py     # Response parser utility
├── CHR_DB_Realtion.yaml      # Database schema definition
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
│
├── .env                      # Environment variables (not in repo)
├── agent_procedure_results.txt  # Agent execution logs (generated)
├── agent_parsed_response.json   # Parsed responses (generated)
└── agent_final_response.txt     # Final answers (generated)
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier | Yes |
| `SNOWFLAKE_USER` | Snowflake username | Yes |
| `SNOWFLAKE_PASSWORD` | Snowflake password | Yes |
| `SNOWFLAKE_DATABASE` | Target database name | Yes |
| `SNOWFLAKE_SCHEMA` | Target schema name | Yes |

### Agent Configuration

The agent name is hardcoded as `CRH_AGENT` in the application. To change it:
- Update `AGENT_NAME` in `streamlit_app.py` (line 100)
- Update `AGENT_NAME` in `agent.py` (line 29)

## Response Format

The agent returns structured responses with the following format:

```
🧠 [PLANNING]: <thinking steps>

🛠️ [TOOL CALL]: <tool_name>
Input: <tool_input_json>

🤖 [FINAL ANSWER]: <final response text>

**Sources:**
- <source_url_1>
- <source_url_2>
```

## Troubleshooting

### Connection Issues
- Verify Snowflake credentials in `.env`
- Check network connectivity
- Ensure Snowflake account is accessible

### Procedure Not Found
- Verify `RUN_CORTEX_AGENT` exists in your schema
- Check procedure name matches exactly
- Ensure you have EXECUTE privilege

### Parsing Errors
- Check response format matches expected structure
- Enable debug mode in Streamlit sidebar
- Review raw response in debug expander

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential. All rights reserved.

## Support

For issues and questions:
- Open an issue on GitHub
- Contact the development team

## Acknowledgments

- Built with Snowflake Cortex Agent
- UI inspired by modern chat interfaces
- Database schema provided by CRH data team

