import json
import subprocess
import shutil


def call_claude(prompt: str, model: str, timeout: int) -> dict:
    if shutil.which('claude') is None:
        raise RuntimeError("claude CLI not found in PATH. Run 'claude --version' to verify installation.")

    result = subprocess.run(
        ['claude', '-p', prompt, '--model', model, '--output-format', 'json'],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr}")

    data = json.loads(result.stdout)
    usage = data.get('usage') or {}
    return {
        'text': data.get('result', ''),
        'cost_usd': data.get('cost_usd') or data.get('total_cost_usd') or 0.0,
        'input_tokens': (
            usage.get('input_tokens')
            or data.get('input_tokens')
            or data.get('total_input_tokens')
            or 0
        ),
        'output_tokens': (
            usage.get('output_tokens')
            or data.get('output_tokens')
            or data.get('total_output_tokens')
            or 0
        ),
    }
