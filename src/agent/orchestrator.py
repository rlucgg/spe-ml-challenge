"""Agent orchestrator: GPT-4o with tool calling for drilling analysis."""

import json
import logging
import time

from openai import OpenAI

from src.config import OPENAI_API_KEY, LLM_MODEL
from src.agent.prompts import SYSTEM_PROMPT
from src.tools.tool_registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10


def create_client() -> OpenAI:
    """Create OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY not set. Set it in .env file or as environment variable."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def ask_question(question: str, verbose: bool = False) -> str:
    """Ask a drilling operations question and get an evidence-based answer.

    Uses GPT-4o with tool calling to query the Volve dataset and synthesize
    a structured answer with evidence from both data and daily reports.

    Args:
        question: The operational question to answer
        verbose: If True, print tool calls and intermediate steps

    Returns:
        Structured answer string
    """
    client = create_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    if verbose:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"{'='*60}\n")

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=4096,
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return f"Error calling LLM: {e}"

        choice = response.choices[0]

        # If the model wants to call tools
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments

                if verbose:
                    print(f"  [Tool Call {round_num + 1}] {fn_name}")
                    try:
                        args_pretty = json.loads(fn_args)
                        for k, v in args_pretty.items():
                            val_str = str(v)
                            if len(val_str) > 100:
                                val_str = val_str[:100] + "..."
                            print(f"    {k}: {val_str}")
                    except json.JSONDecodeError:
                        print(f"    args: {fn_args[:200]}")

                start = time.time()
                result = execute_tool(fn_name, fn_args)
                elapsed = time.time() - start

                if verbose:
                    result_preview = result[:300] + "..." if len(result) > 300 else result
                    print(f"    -> {len(result)} chars in {elapsed:.1f}s")
                    print(f"    Preview: {result_preview}\n")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            continue

        # Model is done (no more tool calls)
        answer = choice.message.content or ""
        if verbose:
            print(f"\n{'='*60}")
            print("Answer generated.")
            print(f"Rounds: {round_num + 1}")
            print(f"{'='*60}\n")
        return answer

    return "Error: Maximum tool calling rounds exceeded. The question may be too complex."
