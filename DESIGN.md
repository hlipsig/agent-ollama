# Design: Triggering and Securing the Ollama Agent

This document describes recommended approaches to trigger the agent workflows in this repository, cross-repo options, and security best practices.

## Approaches

- Repository dispatch (recommended)
  - The triggering repo POSTs to the GitHub REST API `POST /repos/:owner/:repo/dispatches` with an `event_type` (e.g. `run-ollama-agent`) and optional `client_payload`.
  - Advantages: simple, flexible payloads, explicit intent.
  - Example (from triggering repo):
    ```bash
    curl -X POST \
      -H "Authorization: token ${{ secrets.PERSONAL_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/hlipsig/agent-ollama/dispatches \
      -d '{"event_type":"run-ollama-agent","client_payload":{"source_repo":"other/repo","ref":"refs/heads/main"}}'
    ```

- Workflow dispatch by id
  - Trigger a specific workflow file by calling `POST /repos/:owner/:repo/actions/workflows/:workflow_id/dispatches` with `{"ref":"main","inputs":{...}}`.
  - Useful when you want to invoke a particular workflow and pass inputs.

- Webhook relay / GitHub App
  - Build a small service or GitHub App that receives push webhooks from repo A and triggers repo B. This avoids distributing PATs between repos.
  - More secure and auditable for org-wide automation, but requires additional infrastructure and maintenance.

## Self-hosted vs Cloud runners

- Self-hosted runner
  - Recommended when you must run Ollama locally (private models, no cloud instances). Register your runner with label `ollama` and use the provided self-hosted workflows.
  - Benefits: full control over compute, data never leaves your environment, direct access to hardware/GPUs.

- GitHub-hosted runner
  - Easier to run but will pull models on-demand and might incur long startup times or network egress.
  - Use cache keys and smaller models for faster iteration.

## Artifact handling

- Workflows in this repo upload `agent_response.json` and `agent_run_results.json` as artifacts so you can retrieve agent outputs after runs.

## Tokens and Permissions (Security)

- Minimal scopes for classic PATs:
  - Private repo: `repo` (covers dispatch and most repo APIs). For public-only repos `public_repo` may suffice.
  - Optionally `workflow` if you need to interact with workflow-level APIs beyond dispatch.

- Fine-grained PAT (recommended if available):
  - Grant access specifically to `hlipsig/agent-ollama` and set `Actions/Workflows` permission to Read & write (or Workflows Read & write). Limit repository access to the single repo where possible.

- Use repository secrets to store tokens:
  - Store tokens under Settings → Secrets and variables → Actions for the triggering or target repo as appropriate.
  - Example secret name used in this repo: `PERSONAL_TOKEN` (the helper script `scripts/trigger_dispatch.sh` reads this env var).

- Least privilege and rotation:
  - Issue a token with the minimum scopes and scope it to the target repository when possible. Rotate regularly and revoke if compromised.

- Avoid embedding tokens in code or logs. Use `secrets` and ephemeral environment variables locally.

## Recommended triggering snippet for other repos

Add the following step to the other repository's workflow to trigger this repo on push to `main`:

```yaml
- name: Dispatch agent-ollama
  run: |
    curl -sS -X POST \
      -H "Authorization: token ${{ secrets.AGENT_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/hlipsig/agent-ollama/dispatches \
      -d '{"event_type":"run-ollama-agent","client_payload":{"source_repo":"${{ github.repository }}","ref":"${{ github.ref }}","commit":"${{ github.sha }}"}}'
```

Use `AGENT_DISPATCH_TOKEN` as a repository secret in the triggering repo.

## Safety notes

- Running arbitrary commands from an LLM is risky. Use one or more of these mitigations:
  - Require human approval before executing commands (agent outputs commands and opens a PR/issue instead of executing directly).
  - Run the executing step on a locked self-hosted runner with limited privileges and in a dedicated working directory.
  - Sanitize and validate commands returned by the agent; prefer whitelisted operations.

## Next steps and extensions

- Add automatic PR creation instead of direct execution (agent suggests changes and opens PRs for review).
- Add stricter agent prompts and response schema validation to reduce accidental command execution.

## Scheduling / Cron triggers

You can run the workflows on a schedule using GitHub Actions `schedule` (cron). Cron schedules are interpreted in UTC and have a minimum 5-minute granularity.

Examples:

- Daily at 04:00 UTC:

```yaml
on:
  schedule:
    - cron: '0 4 * * *'
  workflow_dispatch:
```

- Weekly on Monday at 02:00 UTC and also on every push to `main`:

```yaml
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'
  workflow_dispatch:
```

Security note for scheduled runs:

- Scheduled workflows behave like any other run: they execute with the repository's `GITHUB_TOKEN` and any secrets available to the workflow. Avoid running high-risk automated commands on a schedule without human review.
- Prefer scheduled runs on self-hosted runners when the model must run locally; ensure the runner is secured and the execution environment is isolated.

### Time zones

- GitHub cron schedules use UTC. When choosing cron timings, convert local times to UTC. For example, US Pacific 21:00 (9pm) is `06:00` UTC next day in winter (PST) or `05:00` in summer (PDT); verify offsets when daylight saving changes apply.
- If you want user-friendly schedule configuration, store preferred timezone and convert before creating cron entries (e.g., via a small scheduling service or when generating workflow files).

### Throttling and concurrency

Long-running model workflows should be throttled to avoid overlapping runs and excessive resource use. Strategies:

- `concurrency` key in workflows — prevents concurrent runs or cancels previous runs automatically. Example (limit to one run at a time):

```yaml
concurrency:
  group: ollama-agent
  cancel-in-progress: false
```

- Use `workflow_run` and `workflow_dispatch` together to chain or gate executions (e.g., don't start heavy runs if a quick smoke test is running).

- On the trigger side, implement simple rate-limiting:
  - The triggering repo can keep a short-lived lock or check a small state service before sending a dispatch.
  - Alternatively, use a dispatch server / GitHub App that enforces rate limits and queues requests.

- On self-hosted runners, limit parallelism by configuring runner labels and `runs-on` selectors so only dedicated runners accept agent jobs.

- For safe retries and backoff, the trigger can retry with exponential backoff if the API returns 429 or if the run queue is full.

### Example schedules (throttled and varied)

- Daily maintenance, run during low-traffic hours (UTC):

```yaml
on:
  schedule:
    - cron: '0 4 * * *'   # daily 04:00 UTC
  workflow_dispatch:
```

- Business-hours summary, weekdays at 15:30 local (UTC example):

```yaml
on:
  schedule:
    - cron: '30 15 * * 1-5'  # 15:30 UTC Mon-Fri
  workflow_dispatch:
```

- Low-frequency throttled run: weekly + manual triggers

```yaml
on:
  schedule:
    - cron: '0 2 * * 1'   # weekly Monday 02:00 UTC
  workflow_dispatch:
```

- Frequent but spaced (every 4 hours), with a concurrency lock to avoid overlaps:

```yaml
concurrency:
  group: ollama-agent-4h
  cancel-in-progress: false

on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:
```

Combine these patterns depending on how often you want the agent to run and how you protect resources.

