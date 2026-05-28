import subprocess
import shutil


def call_claude(prompt: str, model: str, timeout: int) -> str:
    if shutil.which('claude') is None:
        raise RuntimeError("claude CLI not found in PATH. Run 'claude --version' to verify installation.")

    result = subprocess.run(
        ['claude', '-p', prompt, '--model', model],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr}")

    return result.stdout.strip()
