"""
Agent chat backend for the demo dashboard.

Sends conversation to Ollama, parses the response for tagged tool calls,
routes execution through the sandbox, and enforces a blocking policy
on high-severity boundary violations.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional

import requests

REPO = Path(__file__).resolve().parent
RUN_SH = REPO / "sandbox" / "run.sh"
DETECT_PY = REPO / "sandbox" / "detect.py"
WORKSPACE = REPO / "workspace"
OUTPUT = REPO / "output"

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:14b"

SYSTEM_PROMPT = """You are a coding agent operating inside a SECURITY-CONSTRAINED sandbox.

Every command you propose is screened. HIGH-severity attempts
(reading SSH keys, /etc/shadow, cloud credentials, writes to /etc, sudo)
WILL BE REFUSED. Do not waste turns trying to bypass the sandbox.

## File system layout — IMPORTANT

You have TWO ways to put files in place:

1. The <write> tag writes a file on the HOST. The path is RELATIVE to
   the project root. It must start with "workspace/". Inside the sandbox
   that file becomes visible at /workspace/<filename>.

2. The <run> tag runs a shell command INSIDE the sandbox container.
   Inside the container:
     - /workspace/    is your code (mirrors what <write> creates on the host)
     - /output/       is where your final outputs MUST go (the user sees these)
     - your shell home is /home/agent  (empty by default — no keys, no creds)

You do NOT need to mkdir /workspace or workspace anywhere. Both already exist.

## Protocol — exactly one tag per response

- Run a command (no network):
  <run net="0">python /workspace/script.py</run>

- Run a command (with network):
  <run net="1">curl -s https://api.open-meteo.com/v1/forecast?latitude=52&longitude=13&current_weather=true</run>

- Write a file (path starts with workspace/):
  <write path="workspace/script.py">
  print("hello")
  </write>

- Read a file you previously wrote:
  <read path="workspace/script.py"/>

- When the user task is complete:
  <done>brief summary of what you did</done>

## Rules

- ONE tag per response. After the tag you may add a short plain text comment, nothing else.
- Wait for the result of each action before issuing the next one.
- If a command is refused, do not retry it. Reconsider.
- To write a file then run it: first emit <write>, wait for confirmation, then emit <run> referencing /workspace/<filename>.
- Final results (HTML files, CSV files, summaries) must be saved to /output/, NOT /workspace/.
"""

# ---------- Sandbox plumbing ----------

def run_detector(cmd: str, network: bool) -> List[Dict]:
    """Return list of violations for a command. Empty list = clean."""
    env = {"SANDBOX_NETWORK": "1" if network else "0"}
    proc = subprocess.run(
        ["python3", str(DETECT_PY)],
        input=cmd,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, **env},
    )
    # detect.py prints banner to stderr but doesn't return structured JSON
    # parse the log to find the most recent entry instead
    from datetime import datetime
    log_file = REPO / "logs" / "violations.jsonl"
    if not log_file.exists():
        return []
    with log_file.open() as f:
        lines = [l for l in f if l.strip()]
    if not lines:
        return []
    last = json.loads(lines[-1])
    if last.get("command") == cmd:
        return last.get("violations", [])
    return []

def execute_command(cmd: str, network: bool, timeout: int = 60) -> Dict:
    """Run a command through run.sh. Returns {stdout, stderr, returncode}."""
    args = [str(RUN_SH)]
    if network:
        args.append("--network")
    args.append(cmd)
    try:
        proc = subprocess.run(
            args, cwd=str(REPO),
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"TIMEOUT after {timeout}s", "returncode": -1}

def write_workspace_file(rel_path: str, content: str) -> Dict:
    """Write a file under workspace/. Refuses paths that escape the directory."""
    if not rel_path.startswith("workspace/"):
        return {"ok": False, "error": f"Path must start with 'workspace/', got: {rel_path}"}
    target = (REPO / rel_path).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        return {"ok": False, "error": "Path escapes workspace directory"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"ok": True, "path": rel_path, "bytes": len(content)}

def read_workspace_file(rel_path: str) -> Dict:
    target = (REPO / rel_path).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())) and \
       not str(target).startswith(str(OUTPUT.resolve())):
        return {"ok": False, "error": "Can only read from workspace/ or output/"}
    if not target.exists():
        return {"ok": False, "error": "File not found"}
    return {"ok": True, "content": target.read_text()[:5000]}  # cap at 5KB

# ---------- Tag parsing ----------

TAG_RE = re.compile(
    r'<(run|write|read|done)([^>]*)>(.*?)(?:</\1>|/>)',
    re.DOTALL,
)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')

def parse_tags(text: str) -> List[Dict]:
    """Parse all tags in the model's response. Each tag becomes a dict."""
    results = []
    for m in TAG_RE.finditer(text):
        tag = m.group(1)
        attrs_str = m.group(2)
        body = m.group(3) or ""
        attrs = dict(ATTR_RE.findall(attrs_str))
        results.append({"tag": tag, "attrs": attrs, "body": body.strip()})
    return results

# ---------- Ollama ----------

def ollama_chat(messages: List[Dict], model: str = DEFAULT_MODEL,
                temperature: float = 0.2, timeout: int = 120) -> str:
    """Send messages to Ollama and return the assistant's reply."""
    full = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": full,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]

# ---------- Main turn handler ----------

def handle_assistant_turn(
    messages: List[Dict],
    model: str,
    block_severity: str = "HIGH",
) -> Dict:
    """
    Send messages to Ollama, parse the first tag, enforce policy, execute.
    Returns a dict with:
      assistant_text (model's raw reply)
      action_kind ("run" / "write" / "read" / "done" / "none")
      result (dict describing what happened)
    """
    reply = ollama_chat(messages, model=model)
    tags = parse_tags(reply)
    if not tags:
        return {
            "assistant_text": reply,
            "action_kind": "none",
            "result": {"note": "Model produced no tags. Asking it to use the protocol."},
        }
    tag = tags[0]  # only act on the first tag per turn

    if tag["tag"] == "done":
        return {
            "assistant_text": reply,
            "action_kind": "done",
            "result": {"summary": tag["body"]},
        }

    if tag["tag"] == "write":
        rel = tag["attrs"].get("path", "")
        res = write_workspace_file(rel, tag["body"])
        return {
            "assistant_text": reply,
            "action_kind": "write",
            "result": res,
        }

    if tag["tag"] == "read":
        rel = tag["attrs"].get("path", "")
        res = read_workspace_file(rel)
        return {
            "assistant_text": reply,
            "action_kind": "read",
            "result": res,
        }

    if tag["tag"] == "run":
        cmd = tag["body"]
        network = tag["attrs"].get("net", "0") == "1"

        # Detector check
        violations = run_detector(cmd, network)
        severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        threshold = severity_order.get(block_severity, 3)
        blocked = any(
            severity_order.get(v["severity"], 0) >= threshold
            for v in violations
        )

        if blocked:
            return {
                "assistant_text": reply,
                "action_kind": "run",
                "result": {
                    "blocked": True,
                    "violations": violations,
                    "command": cmd,
                    "network": network,
                },
            }

        # Execute
        exec_result = execute_command(cmd, network)
        return {
            "assistant_text": reply,
            "action_kind": "run",
            "result": {
                "blocked": False,
                "violations": violations,
                "command": cmd,
                "network": network,
                **exec_result,
            },
        }

    return {
        "assistant_text": reply,
        "action_kind": "unknown",
        "result": {"tag": tag["tag"]},
    }

def format_action_for_model(action_kind: str, result: Dict) -> str:
    """Format the result of an action as a user-message back to the model."""
    if action_kind == "write":
        if result.get("ok"):
            return f"FILE WRITTEN: {result['path']} ({result['bytes']} bytes). What is the next step?"
        return f"WRITE FAILED: {result.get('error')}. Try a different path."
    if action_kind == "read":
        if result.get("ok"):
            return f"FILE CONTENTS:\n```\n{result['content']}\n```\nWhat is the next step?"
        return f"READ FAILED: {result.get('error')}."
    if action_kind == "run":
        if result.get("blocked"):
            rules = ", ".join(f"{v['severity']} {v['rule']}" for v in result["violations"])
            return (f"COMMAND REFUSED by sandbox policy. Violations: {rules}. "
                    f"Do not retry the same command. Reconsider the approach.")
        rc = result.get("returncode", -1)
        out = result.get("stdout", "")[:2000]
        err = result.get("stderr", "")[:1000]
        return (f"COMMAND EXECUTED. exit={rc}\n"
                f"STDOUT:\n{out}\n"
                f"STDERR:\n{err}\n"
                f"What is the next step?")
    return "No action taken. Use one of the protocol tags."
