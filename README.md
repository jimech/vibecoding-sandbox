# AI Coding Agent Sandbox

This project presents a sandboxed execution environment for evaluating AI coding agents under security constraints. The goal is to demonstrate how agent-generated code and shell commands can be executed in a controlled environment while reducing the risk of unsafe system access, credential leakage, or unintended host modification.

The system combines a local AI model, a Streamlit-based demonstration interface, Docker isolation, and a boundary-violation detection layer. It is designed as an experimental framework for studying how AI coding assistants can be made safer when interacting with real development environments.

## Motivation

AI coding agents are increasingly capable of generating and executing commands, modifying files, and interacting with development infrastructure. While this makes them useful for automation and software engineering tasks, it also introduces security risks. An agent may accidentally or intentionally attempt to access sensitive files, leak credentials, modify system directories, or execute commands outside the intended project scope.

This project explores a defense-in-depth approach for running AI coding agents more safely. Instead of allowing generated commands to execute directly on the host machine, commands are routed through a sandbox and inspected before execution. High-risk behavior is detected and blocked, while benign development tasks can continue in a controlled environment.

## System Overview

The application provides a Streamlit dashboard that demonstrates secure agent interaction. A local coding model generates proposed actions, and each action is screened before execution. Commands are executed inside an isolated Docker-based runtime rather than directly on the host system.

The dashboard includes:

* A local AI coding agent powered by Ollama
* A Streamlit interface for observing and interacting with the system
* Docker-based sandbox execution
* Optional gVisor-based sandbox wrapper
* Boundary-violation detection for unsafe commands
* Logging of detected violations and execution behavior
* Demonstrations of benign tasks and pre-built attack scenarios

## Security Objective

The main security objective is to reduce the attack surface of AI-assisted coding workflows. The system is designed to prevent or contain actions such as:

* Reading private SSH keys or credentials
* Accessing sensitive system files
* Writing to protected host directories
* Running privileged commands
* Attempting sandbox escape behavior
* Leaking sensitive data into output files
* Executing high-risk commands without inspection

The sandbox does not claim to eliminate all possible vulnerabilities. Instead, it provides a practical demonstration of layered mitigation techniques for safer AI-agent execution.

## Architecture

The system follows a modular architecture:

1. The user interacts with the Streamlit dashboard.
2. The AI agent generates a proposed command or file operation.
3. The detector analyzes the proposed action for boundary violations.
4. High-severity actions are blocked before execution.
5. Allowed commands are executed inside the sandbox runtime.
6. Results and violations are logged for later inspection.

This design separates agent reasoning, policy enforcement, execution, and observation.

## Screenshots

### Chat with Agent

![Chat with agent](docs/images/streamlit-chat.png)

### Dashboard Overview

![Dashboard](docs/images/streamlit-dashboard.png)

### Live Sandbox Execution

![Live sandbox](docs/images/streamlit-live.png)

## Key Files

* `demo_app.py` — Main Streamlit dashboard
* `agent_chat.py` — Agent backend and Ollama integration
* `sandbox/run.sh` — Standard Docker sandbox execution wrapper
* `sandbox/run_gvisor.sh` — gVisor sandbox execution wrapper
* `sandbox/detect.py` — Boundary-violation detection logic
* `logs/violations.jsonl` — Structured log of detected violations
* `docs/observations.md` — Notes and observations from experiments

## Running the Project

Start the local Ollama model:

```bash
ollama run qwen2.5-coder:14b
```

In a separate terminal, launch the Streamlit dashboard:

```bash
streamlit run demo_app.py
```

The application will open a browser-based dashboard where the user can test sandboxed commands, run predefined scenarios, and interact with the AI coding agent.

## Example Use Cases

This sandbox can be used to:

* Evaluate how AI coding agents behave when given risky prompts
* Test command-filtering and boundary-detection policies
* Demonstrate safe execution of generated code
* Compare benign coding tasks with adversarial scenarios
* Study the limitations of sandboxing and agent-level guardrails

## Limitations

This project is a research and educational prototype. It should not be treated as a complete production security solution. The sandbox and detector reduce risk, but they may not cover every possible attack path. Real-world deployment would require stronger isolation, continuous policy updates, monitoring, access control, and formal security review.

## Conclusion

The project demonstrates that AI coding agents can be made safer by combining local model execution with sandboxing, command inspection, and structured violation logging. This approach helps preserve the usefulness of AI-assisted development while reducing the likelihood of harmful or unintended system behavior.
