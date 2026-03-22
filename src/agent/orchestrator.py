"""Agent orchestrator: GPT-5.4 mini with tool calling for drilling analysis."""

import json
import logging
import time
from typing import Optional

from openai import OpenAI

from src.config import OPENAI_API_KEY, LLM_MODEL, REASONING_EFFORT
from src.agent.prompts import SYSTEM_PROMPT
from src.tools.tool_registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10
MAX_RETRIES = 3


def create_client() -> OpenAI:
    """Create OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY not set. Set it in .env file or as environment variable."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def _is_retryable(error: Exception) -> bool:
    """Check if an API error is retryable (rate limit, server error, timeout)."""
    err_str = str(error).lower()
    if "rate" in err_str or "429" in err_str:
        return True
    if any(code in err_str for code in ["500", "502", "503", "timeout", "connection"]):
        return True
    return False


# Module-level state for sticky fallback across rounds
_use_reasoning_effort = True
_use_max_completion_tokens = True


def _build_create_kwargs(messages: list, tools: list) -> dict:
    """Build kwargs for chat completions, handling reasoning_effort compatibility."""
    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": tools,
    }
    if _use_reasoning_effort and REASONING_EFFORT and REASONING_EFFORT != "none":
        kwargs["reasoning_effort"] = REASONING_EFFORT
    else:
        kwargs["temperature"] = 0.1

    if _use_max_completion_tokens:
        kwargs["max_completion_tokens"] = 4096
    else:
        kwargs["max_tokens"] = 4096
    return kwargs


def _call_with_retry(client: OpenAI, messages: list, tools: list) -> object:
    """Call OpenAI API with exponential backoff retry on transient errors."""
    global _use_reasoning_effort, _use_max_completion_tokens
    kwargs = _build_create_kwargs(messages, tools)

    for attempt in range(MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            err_str = str(e)
            # Sticky fallback: disable reasoning_effort for all future calls
            if "reasoning_effort" in err_str or ("reasoning" in err_str.lower() and "not supported" in err_str.lower()):
                logger.info("reasoning_effort not supported with tools, using temperature fallback")
                _use_reasoning_effort = False
                kwargs.pop("reasoning_effort", None)
                kwargs["temperature"] = 0.1
                return client.chat.completions.create(**kwargs)
            if "max_completion_tokens" in err_str:
                logger.info("max_completion_tokens not supported, using max_tokens")
                _use_max_completion_tokens = False
                val = kwargs.pop("max_completion_tokens", 4096)
                kwargs["max_tokens"] = val
                return client.chat.completions.create(**kwargs)

            if attempt < MAX_RETRIES - 1 and _is_retryable(e):
                wait = 2 ** attempt
                logger.warning(
                    "API call failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, MAX_RETRIES, wait, e,
                )
                time.sleep(wait)
            else:
                raise


def ask_question(
    question: str,
    verbose: bool = False,
    trace: bool = False,
) -> str:
    """Ask a drilling operations question and get an evidence-based answer.

    Args:
        question: The operational question to answer
        verbose: If True, print tool calls and intermediate steps to stdout
        trace: If True, append an Evidence Trace section to the answer

    Returns:
        Structured answer string (with evidence trace if trace=True)
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

    trace_steps = []
    data_sources_used = set()
    total_tool_time = 0.0
    tool_call_count = 0

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = _call_with_retry(client, messages, TOOL_DEFINITIONS)
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return f"Error calling LLM: {e}"

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = tool_call.function.arguments
                tool_call_count += 1

                if verbose:
                    print(f"  [Tool Call {tool_call_count}] {fn_name}")
                    try:
                        args_pretty = json.loads(fn_args)
                        for k, v in args_pretty.items():
                            val_str = str(v)
                            if len(val_str) > 100:
                                val_str = val_str[:100] + "..."
                            print(f"    {k}: {val_str}")
                    except json.JSONDecodeError:
                        print(f"    args: {fn_args[:200]}")

                start_t = time.time()
                result = execute_tool(fn_name, fn_args)
                elapsed = time.time() - start_t
                total_tool_time += elapsed

                if verbose:
                    preview = result[:300] + "..." if len(result) > 300 else result
                    print(f"    -> {len(result)} chars in {elapsed:.2f}s")
                    print(f"    Preview: {preview}\n")

                # Build trace step
                if trace:
                    try:
                        args_dict = json.loads(fn_args)
                        args_str = ", ".join(
                            f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"
                            for k, v in args_dict.items()
                        )
                    except json.JSONDecodeError:
                        args_str = fn_args[:100]

                    summary = result[:500].replace("\n", " ")
                    trace_steps.append({
                        "step": tool_call_count,
                        "tool": fn_name,
                        "args": args_str,
                        "result_len": len(result),
                        "duration": elapsed,
                        "summary": summary,
                    })

                    # Track data sources
                    if "ddr_status" in result or "ddr_activities" in result or fn_name in ("get_well_overview", "get_drilling_phases", "compute_efficiency_metrics"):
                        data_sources_used.add("ddr_status")
                        data_sources_used.add("ddr_activities")
                    if "witsml" in fn_args.lower() or fn_name == "get_bha_configurations":
                        data_sources_used.add("witsml_mudlog")
                        data_sources_used.add("witsml_bha_runs")
                    if fn_name == "search_daily_reports":
                        data_sources_used.add("vectorstore")
                    if fn_name == "get_formation_context":
                        data_sources_used.add("formation_tops")
                    if fn_name == "query_drilling_data":
                        for tbl in ["ddr_status", "ddr_activities", "ddr_fluids",
                                     "witsml_mudlog", "witsml_bha_runs", "formation_tops",
                                     "production", "witsml_trajectory", "witsml_messages"]:
                            if tbl in fn_args:
                                data_sources_used.add(tbl)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            continue

        # Model is done
        answer = choice.message.content or ""
        if verbose:
            print(f"\n{'='*60}")
            print(f"Answer generated. Tool calls: {tool_call_count}, Rounds: {round_num + 1}")
            print(f"{'='*60}\n")

        # Append evidence trace if requested
        if trace and trace_steps:
            answer += _format_trace(trace_steps, total_tool_time, data_sources_used)

        return answer

    return "Error: Maximum tool calling rounds exceeded. The question may be too complex."


def _format_trace(
    steps: list[dict],
    total_time: float,
    data_sources: set[str],
) -> str:
    """Format the evidence trace as a markdown section."""
    lines = ["\n\n## Evidence Trace\n"]
    for s in steps:
        lines.append(f"### Step {s['step']}: {s['tool']}({s['args']})")
        lines.append(f"Retrieved: {s['result_len']} chars | Duration: {s['duration']:.2f}s")
        lines.append(f"Summary: {s['summary'][:300]}")
        lines.append("")

    lines.append(f"**Total tool calls: {len(steps)} | "
                 f"Total evidence retrieval time: {total_time:.2f}s**")
    if data_sources:
        lines.append(f"**Data sources used: {', '.join(sorted(data_sources))}**")

    return "\n".join(lines)
