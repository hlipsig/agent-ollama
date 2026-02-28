## Ollama Agent — Quickstart & How It Works

TL;DR

- Run the agent: either on a self-hosted runner (recommended for local models) or in cloud Actions. It produces `agent_response.json` and `agent_run_results.json` artifacts.
- Safety: the agent uses an allowlist and a two-stage run (prepare → approve → execute). Prefer the PR workflow for production changes.
- Files to skim immediately: [agent-config.json](agent-config.json), [scripts/execute_commands.py](scripts/execute_commands.py), [DESIGN.md](DESIGN.md), [README.md](README.md).

Quick setup (5 minutes)

1. Prereqs
   - A GitHub repository with admin access.
   - If you want local model runs: install Ollama on the machine you will use as a runner (https://ollama.com/docs).
   - A fine-grained or classic personal access token with repo + workflow permissions for dispatching (store it in a repo secret named `PERSONAL_TOKEN`).

2. Register a self-hosted runner (optional but recommended for running models locally)
   - Settings → Actions → Runners → Add runner. During registration add label `ollama`.
   - Ensure the runner user can invoke `ollama` and run the repo checkout.

3. Create the approval environment
   - Settings → Environments → New environment → name it `agent-approval`.
   - Add required reviewers or protection rules so the workflow's `execute` job pauses until someone approves.

4. Configure secrets
   - Add `PERSONAL_TOKEN` (dispatch token) in Settings → Secrets and variables → Actions.

Run the agent (three safe ways)

- Self-hosted, approval-gated (recommended for production-grade ops):
  1. Trigger `Ollama Agent (Self-hosted)` from Actions or send a `repository_dispatch`.
  2. Workflow `prepare` job runs the model, writes `agent_response.json`, and validates commands against the allowlist.
 3. The `execute` job is bound to the `agent-approval` environment and will wait for manual approval before running allowed commands.

- PR proposal (human-in-the-loop):
  - Use the `Ollama Agent (Propose PR)` workflow. It runs the agent and opens a branch + PR containing `AGENT_PROPOSAL.md`. Humans review and merge.

- Cloud-only (fast experiments):
  - Use the cloud workflow or change to a smaller model (`tinyllama`) to iterate quicker. Expect long cold-start time for large models.

How it works — concise flow

1. `agent-config.json` — repo-local config. Key fields:
   - `working_dir` — where to run commands.
   - `commands` — fallback/static commands.
   - `allowlist` — array of regex patterns; commands must match at least one pattern to be considered allowed.

2. GitHub Action calls Ollama via `ai-action/ollama-action` and returns a string response (expected JSON). The workflow saves that to `agent_response.json`.

3. `scripts/execute_commands.py` parses the agent response and supports two modes:
   - `validate`: only validates suggested commands against the `allowlist`, writes `agent_run_results.json` with the validation details.
   - `execute`: runs only the commands that match the `allowlist` and records stdout/stderr/return codes.

4. Artifacts: both the raw `agent_response.json` and `agent_run_results.json` are uploaded as Actions artifacts for auditing.

5. Approval gate: the self-hosted workflow separates jobs into `prepare` and `execute`. The `execute` job uses `environment: agent-approval`, causing GitHub to pause and require reviewer approval.

6. PR workflow: instead of executing, the `ollama-agent-pr.yml` workflow creates `AGENT_PROPOSAL.md` and opens a PR using `peter-evans/create-pull-request` so humans review changes.

Safety checklist (what to enable)

- Use an `allowlist` and keep it conservative; prefer whitelisting short subcommands (e.g., `^echo\\s+`, `^npm\\s+audit\\s+fix`).
- Default to `validate` / dry-run; require `execute` only after human approval.
- Use the PR workflow for non-trivial changes — CI runs on the PR before merge.
- Keep dispatch tokens scoped and rotate regularly. Avoid embedding tokens in code.

Quick test & troubleshooting

- Run unit tests locally:

```bash
python3 -m unittest discover -v tests
```

- Validate a sample agent response locally:

```bash
python3 scripts/execute_commands.py agent-config.json sample_agent_response.json validate
```

- Execute allowed commands locally (beware destructive commands):

```bash
python3 scripts/execute_commands.py agent-config.json sample_agent_response.json execute
```

Files & entry points (where to look)

- [agent-config.json](agent-config.json) — config + allowlist.
- [scripts/execute_commands.py](scripts/execute_commands.py) — validator and executor (modes: `validate`, `execute`).
- [.github/workflows/ollama-agent-selfhosted.yml](.github/workflows/ollama-agent-selfhosted.yml) — prepare + approval-gated execute.
- [.github/workflows/ollama-agent-pr.yml](.github/workflows/ollama-agent-pr.yml) — PR proposal flow.
- [.github/workflows/ci.yml](.github/workflows/ci.yml) — runs unit tests.
- [DESIGN.md](DESIGN.md) — detailed design, scheduling, throttling, security notes.

Next experimentation ideas (short)

- Experimental reviewer: add a lightweight "peer-review" step where a secondary agent evaluates suggested commands and provides a score/opinion; use this as advisory guidance before human approval.
- Policy engine: integrate OPA/Rego to express organizational constraints and run a policy check during `validate`.
- Monitoring & alerting: capture metrics for agent proposals and execution frequency, and add a repo-level kill-switch.

Questions or want me to open a PR with these docs? Reply with which next step you prefer.
