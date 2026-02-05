# app/criteria_checker.py
"""
Module for evaluating completion criteria on LLM outputs.
Supports multiple criteria types: contains, regex, json_valid, code_block, llm_judge, always_pass
"""
import re
import json
from typing import Tuple, Optional
from .models import CriteriaType


def extract_code_blocks(text: str) -> list[str]:
    """Extract code blocks from markdown-formatted text."""
    # Match ```language\ncode\n``` or ```\ncode\n```
    pattern = r'```(?:\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


def check_contains(output: str, criteria_value: str) -> Tuple[bool, str]:
    """Check if output contains the specified string."""
    if not criteria_value:
        return False, "No string specified to search for"
    
    if criteria_value.lower() in output.lower():
        return True, f"Output contains '{criteria_value}'"
    else:
        return False, f"Output does not contain '{criteria_value}'"


def check_regex(output: str, criteria_value: str) -> Tuple[bool, str]:
    """Check if output matches the regex pattern."""
    if not criteria_value:
        return False, "No regex pattern specified"
    
    try:
        pattern = re.compile(criteria_value, re.IGNORECASE | re.MULTILINE)
        match = pattern.search(output)
        if match:
            return True, f"Output matches pattern. Found: '{match.group()[:100]}'"
        else:
            return False, f"Output does not match pattern '{criteria_value}'"
    except re.error as e:
        return False, f"Invalid regex pattern: {str(e)}"


def check_json_valid(output: str) -> Tuple[bool, str]:
    """Check if output is valid JSON or contains valid JSON."""
    # Try to parse the entire output as JSON
    try:
        json.loads(output.strip())
        return True, "Output is valid JSON"
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from code blocks first (common format)
    code_blocks = extract_code_blocks(output)
    for block in code_blocks:
        try:
            json.loads(block.strip())
            return True, f"Found valid JSON in code block"
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON by locating outermost { } or [ ]
    # This handles nested JSON properly
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = output.find(start_char)
        if start_idx == -1:
            continue
        
        # Find the matching closing bracket by counting
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(output[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    # Found matching bracket
                    json_str = output[start_idx:i+1]
                    try:
                        json.loads(json_str)
                        return True, f"Found valid JSON ({len(json_str)} chars)"
                    except json.JSONDecodeError:
                        break  # Try next occurrence
    
    return False, "Output does not contain valid JSON"


def check_code_block(output: str, criteria_value: Optional[str] = None) -> Tuple[bool, str]:
    """Check if output contains code blocks, optionally of a specific language."""
    code_blocks = extract_code_blocks(output)
    
    if not code_blocks:
        # Also check for indented code blocks (4 spaces or tab)
        indented_pattern = r'(?:^|\n)((?:    |\t).+(?:\n(?:    |\t).+)*)'
        indented_matches = re.findall(indented_pattern, output)
        if indented_matches:
            code_blocks = indented_matches
    
    if not code_blocks:
        return False, "No code blocks found in output"
    
    if criteria_value:
        # Check for specific language
        lang_pattern = rf'```{criteria_value}\n'
        if re.search(lang_pattern, output, re.IGNORECASE):
            return True, f"Found {len(code_blocks)} code block(s) with language '{criteria_value}'"
        else:
            return False, f"Found {len(code_blocks)} code block(s) but none with language '{criteria_value}'"
    
    return True, f"Found {len(code_blocks)} code block(s) in output"


async def check_llm_judge(
    output: str, 
    criteria_value: str, 
    original_prompt: str
) -> Tuple[bool, str]:
    """Use an LLM to judge if output meets criteria."""
    from .unbound_client import call_llm_for_judgment
    
    if not criteria_value:
        return False, "No criteria specified for LLM judgment"
    
    result = await call_llm_for_judgment(
        prompt=original_prompt,
        llm_output=output,
        criteria=criteria_value
    )
    
    return result["passed"], result["explanation"]


async def evaluate_criteria(
    output: str,
    criteria_type: CriteriaType,
    criteria_value: Optional[str],
    original_prompt: str = ""
) -> Tuple[bool, str]:
    """
    Evaluate if output meets the specified criteria.
    
    Args:
        output: The LLM output to evaluate
        criteria_type: The type of criteria to apply
        criteria_value: The value/pattern for the criteria (if applicable)
        original_prompt: The original prompt (used for LLM judge)
    
    Returns:
        Tuple of (passed: bool, details: str)
    """
    if criteria_type == CriteriaType.ALWAYS_PASS:
        return True, "Always pass criteria - step automatically succeeds"
    
    elif criteria_type == CriteriaType.CONTAINS:
        return check_contains(output, criteria_value or "")
    
    elif criteria_type == CriteriaType.REGEX:
        return check_regex(output, criteria_value or "")
    
    elif criteria_type == CriteriaType.JSON_VALID:
        return check_json_valid(output)
    
    elif criteria_type == CriteriaType.CODE_BLOCK:
        return check_code_block(output, criteria_value)
    
    elif criteria_type == CriteriaType.LLM_JUDGE:
        return await check_llm_judge(output, criteria_value or "", original_prompt)
    
    else:
        return False, f"Unknown criteria type: {criteria_type}"


def extract_context(
    output: str,
    context_mode: str,
    context_template: Optional[str] = None
) -> str:
    """
    Extract context from output to pass to the next step.
    
    Args:
        output: The full LLM output
        context_mode: How to extract context (full, code_only, summary, custom)
        context_template: Custom extraction template (for custom mode)
    
    Returns:
        Extracted context string
    """
    from .models import ContextPassingMode
    
    if context_mode == ContextPassingMode.FULL or context_mode == "full":
        return output
    
    elif context_mode == ContextPassingMode.CODE_ONLY or context_mode == "code_only":
        code_blocks = extract_code_blocks(output)
        if code_blocks:
            return "\n\n".join(f"```\n{block}\n```" for block in code_blocks)
        else:
            return output  # Fallback to full if no code blocks
    
    elif context_mode == ContextPassingMode.SUMMARY or context_mode == "summary":
        # Summary is handled async in the executor
        return output
    
    elif context_mode == ContextPassingMode.CUSTOM or context_mode == "custom":
        if context_template:
            # Simple template replacement
            # Users can define patterns like {{output}} or {{code}}
            result = context_template
            result = result.replace("{{output}}", output)
            
            code_blocks = extract_code_blocks(output)
            if code_blocks:
                result = result.replace("{{code}}", "\n".join(code_blocks))
            else:
                result = result.replace("{{code}}", "")
            
            return result
        else:
            return output
    
    return output
