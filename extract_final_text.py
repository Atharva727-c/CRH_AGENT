#!/usr/bin/env python3
"""
Extract the final text response, thinking steps, tool calls, and sources from the agent results
"""
import json
import re

# Read the results file
with open('agent_procedure_results.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the AGENT RESPONSE section
start_marker = "AGENT RESPONSE:"
start_idx = content.find(start_marker)

if start_idx != -1:
    # Extract everything after AGENT RESPONSE
    response_text = content[start_idx + len(start_marker):].strip()
    
    # Remove the separator line if present
    response_text = response_text.lstrip('=').strip()
    
    # Parse the new format
    thinking_steps = []
    tool_calls = []
    final_answer = None
    sources = []
    
    # Split by sections
    # Pattern: 🧠 [PLANNING]:, 🛠️ [TOOL CALL]:, 🤖 [FINAL ANSWER]:, **Sources:**
    
    # Extract thinking steps (🧠 [PLANNING]:)
    planning_pattern = r'🧠\s*\[PLANNING\]:\s*(.*?)(?=🧠\s*\[PLANNING\]:|🛠️\s*\[TOOL CALL\]:|🤖\s*\[FINAL ANSWER\]:|\*\*Sources:\*\*|$)'
    planning_matches = re.findall(planning_pattern, response_text, re.DOTALL)
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
    tool_call_matches = re.findall(tool_call_pattern, response_text, re.DOTALL)
    for tool_name, tool_input in tool_call_matches:
        try:
            # Try to parse the input as JSON
            input_data = json.loads(tool_input)
        except:
            input_data = tool_input
        tool_calls.append({
            "tool": tool_name,
            "input": input_data
        })
    
    # Extract final answer (🤖 [FINAL ANSWER]:)
    final_answer_pattern = r'🤖\s*\[FINAL ANSWER\]:\s*(.*?)(?=\*\*Sources:\*\*|$)'
    final_answer_match = re.search(final_answer_pattern, response_text, re.DOTALL)
    if final_answer_match:
        final_answer = final_answer_match.group(1).strip()
    
    # Extract sources (**Sources:**)
    sources_pattern = r'\*\*Sources:\*\*\s*\n(.*?)(?=🧠|🛠️|🤖|$)'
    sources_match = re.search(sources_pattern, response_text, re.DOTALL)
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
    if not final_answer:
        # Try to find text after the last tool call or planning step
        parts = re.split(r'(🧠\s*\[PLANNING\]:|🛠️\s*\[TOOL CALL\]:|🤖\s*\[FINAL ANSWER\]:|\*\*Sources:\*\*)', response_text)
        if len(parts) > 1:
            # Get the last meaningful text section
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] and not parts[i].startswith('🧠') and not parts[i].startswith('🛠️') and not parts[i].startswith('🤖') and not parts[i].startswith('**'):
                    potential_answer = parts[i].strip()
                    if potential_answer and len(potential_answer) > 20:  # Reasonable length
                        final_answer = potential_answer
                        break
    
    # Print results
    print("="*70)
    print("EXTRACTED AGENT RESPONSE:")
    print("="*70)
    
    if thinking_steps:
        print(f"\n🧠 THINKING STEPS ({len(thinking_steps)}):")
        for i, step in enumerate(thinking_steps, 1):
            print(f"\n  Step {i}:")
            print(f"  {step['description']}")
    
    if tool_calls:
        print(f"\n🛠️ TOOL CALLS ({len(tool_calls)}):")
        for i, tool_call in enumerate(tool_calls, 1):
            print(f"\n  Tool Call {i}:")
            print(f"  Tool: {tool_call['tool']}")
            print(f"  Input: {json.dumps(tool_call['input'], indent=2)}")
    
    if final_answer:
        print(f"\n🤖 FINAL ANSWER:")
        print(final_answer)
    
    if sources:
        print(f"\n🔗 SOURCES ({len(sources)}):")
        for i, source in enumerate(sources, 1):
            print(f"  {i}. {source['url']}")
    
    print("\n" + "="*70)
    
    # Save to JSON file for easy consumption
    output_data = {
        "thinking_steps": thinking_steps,
        "tool_calls": tool_calls,
        "final_answer": final_answer,
        "sources": sources
    }
    
    with open('agent_parsed_response.json', 'w', encoding='utf-8') as out:
        json.dump(output_data, out, indent=2, ensure_ascii=False)
    print("\n✓ Saved parsed response to: agent_parsed_response.json")
    
    # Also save final answer to text file
    if final_answer:
        with open('agent_final_response.txt', 'w', encoding='utf-8') as out:
            out.write(final_answer)
        print("✓ Saved final answer to: agent_final_response.txt")
    
else:
    print("Could not find AGENT RESPONSE section")
