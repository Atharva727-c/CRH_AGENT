#!/usr/bin/env python3
"""
Test script for Snowflake Cortex Agent CRH_AGENT using stored procedure
This calls the RUN_CORTEX_AGENT stored procedure that uses _snowflake.send_snow_api_request
"""
import os
import sys
import json
from dotenv import load_dotenv
import snowflake.connector

# Configure output
output_file = open('agent_procedure_results.txt', 'w', encoding='utf-8')

def log(message):
    """Log to both console and file"""
    print(message, flush=True)
    output_file.write(message + '\n')
    output_file.flush()

load_dotenv()

# Configuration
ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
USER = os.getenv('SNOWFLAKE_USER')
PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
AGENT_NAME = "CRH_AGENT"
PROMPT = "How is Avient's first quarter result?"

# Procedure name - try both variants
PROCEDURE_NAMES = [
    "RUN_CORTEX_AGENT",  # From your CALL statement
    "RUN_CORTEX_AGENT_TEXT_ONLY",  # From your CREATE statement
]

log("="*70)
log("Snowflake Cortex Agent Test - Using Stored Procedure")
log("="*70)
log(f"Account: {ACCOUNT}")
log(f"Database: {DATABASE}")
log(f"Schema: {SCHEMA}")
log(f"Agent: {AGENT_NAME}")
log(f"Prompt: {PROMPT}")
log("")

# Step 1: Connect to Snowflake
log("[Step 1/2] Connecting to Snowflake...")
try:
    conn = snowflake.connector.connect(
        user=USER,
        password=PASSWORD,
        account=ACCOUNT,
        database=DATABASE,
        schema=SCHEMA,
        login_timeout=20
    )
    log("✓ Successfully connected to Snowflake")
except Exception as e:
    log(f"✗ Connection failed: {e}")
    output_file.close()
    sys.exit(1)

# Step 2: Call the stored procedure
log(f"\n[Step 2/2] Calling stored procedure to run agent...")
log("  This may take a few minutes (up to 15 minutes)...")

success = False
for proc_name in PROCEDURE_NAMES:
    try:
        cursor = conn.cursor()
        
        # Try to find the procedure
        log(f"\n  Looking for procedure: {proc_name}")
        
        # First, check if procedure exists
        try:
            cursor.execute(f"SHOW PROCEDURES LIKE '{proc_name}' IN SCHEMA {DATABASE}.{SCHEMA}")
            procedures = cursor.fetchall()
            
            if not procedures:
                log(f"    Procedure '{proc_name}' not found in {DATABASE}.{SCHEMA}")
                # Try without schema qualification
                cursor.execute(f"SHOW PROCEDURES LIKE '{proc_name}'")
                procedures = cursor.fetchall()
        except:
            procedures = []
        
        # Try calling the procedure
        # Escape single quotes in the prompt
        escaped_prompt = PROMPT.replace("'", "''")
        
        # Try different call formats
        call_queries = [
            f"CALL {DATABASE}.{SCHEMA}.{proc_name}('{DATABASE}', '{SCHEMA}', '{AGENT_NAME}', '{escaped_prompt}')",
            f"CALL {SCHEMA}.{proc_name}('{DATABASE}', '{SCHEMA}', '{AGENT_NAME}', '{escaped_prompt}')",
            f"CALL {proc_name}('{DATABASE}', '{SCHEMA}', '{AGENT_NAME}', '{escaped_prompt}')",
        ]
        
        for call_query in call_queries:
            try:
                log(f"    Executing: {call_query[:100]}...")
                cursor.execute(call_query)
                
                # Get the result
                result = cursor.fetchone()
                
                if result:
                    log("\n" + "="*70)
                    log("AGENT RESPONSE:")
                    log("="*70)
                    
                    # The result is a tuple, get the first element (the return value)
                    response = result[0] if isinstance(result, tuple) else result
                    
                    # The response is now a formatted text string with:
                    # 🧠 [PLANNING]: sections
                    # 🛠️ [TOOL CALL]: sections
                    # 🤖 [FINAL ANSWER]: section
                    # **Sources:** section
                    if isinstance(response, str):
                        # Just log the response as-is (it's already formatted)
                        log("")
                        log(response)
                        log("")
                    else:
                        log(str(response))
                    
                    log("="*70)
                    success = True
                    break
                else:
                    log("    No result returned")
                    
            except snowflake.connector.errors.ProgrammingError as e:
                error_msg = str(e)
                if "does not exist" in error_msg.lower():
                    log(f"    Procedure not found with this format")
                    continue
                elif "incorrect number of arguments" in error_msg.lower():
                    log(f"    Wrong number of arguments: {error_msg[:150]}")
                    continue
                else:
                    log(f"    Error: {error_msg[:200]}")
                    continue
            except Exception as e:
                log(f"    Error: {type(e).__name__}: {str(e)[:200]}")
                continue
        
        cursor.close()
        
        if success:
            break
            
    except Exception as e:
        log(f"  Error trying procedure {proc_name}: {type(e).__name__}: {str(e)[:200]}")
        continue

if not success:
    log("\n" + "="*70)
    log("Could not call the stored procedure")
    log("="*70)
    log("\nPlease ensure:")
    log(f"1. The procedure exists in {DATABASE}.{SCHEMA}")
    log("2. The procedure name matches (RUN_CORTEX_AGENT or RUN_CORTEX_AGENT_TEXT_ONLY)")
    log("3. You have EXECUTE privilege on the procedure")
    log("4. The procedure signature matches: (AGENT_DB, AGENT_SCHEMA, AGENT_NAME, USER_QUERY)")
    log("\nYou can verify the procedure exists with:")
    log(f"  SHOW PROCEDURES LIKE 'RUN_CORTEX_AGENT%' IN SCHEMA {DATABASE}.{SCHEMA};")

conn.close()
log("\n✓ Connection closed")

log("\n" + "="*70)
log("Test completed. Results saved to: agent_procedure_results.txt")
log("="*70)

output_file.close()

