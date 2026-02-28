# Ollama Agent GitHub Action Example

This repo contains a GitHub Actions workflow that uses the `ai-action/ollama-action` to run an agent which can suggest commands to run against this repository. For demo purposes the agent will return dummy upgrade commands defined in `agent-config.json` or in its generated response.

Usage:

- Trigger the workflow via `Actions -> Ollama Agent Runner -> Run workflow` (workflow_dispatch), or send a `repository_dispatch` event.
- The action will call the Ollama model, save the JSON response to `agent_response.json`, and run `scripts/execute_commands.py` to execute suggested commands.

Files added:

- `.github/workflows/ollama-agent.yml` - workflow that runs the agent.
- `agent-config.json` - configuration with `working_dir` and `commands` list.
- `scripts/execute_commands.py` - reads the agent response and executes commands, writing `agent_run_results.json`.

You may edit `agent-config.json` to point to a different folder or change the dummy commands.

Triggering via repository_dispatch
- A `repository_dispatch` event can start the workflow. Example methods:

- Using the `gh` CLI (recommended if authenticated):

```bash
gh api --method POST /repos/scottscott/agent-ollama/dispatches \
	-f event_type=run-ollama-agent \
	-f client_payload='{ "reason": "manual-test" }'
```

- Using `curl` with a token in `GITHUB_TOKEN` or `PERSONAL_TOKEN` env var:

```bash
export PERSONAL_TOKEN="<your_token_with_repo_scope>"
export OWNER=scottscott
export REPO=agent-ollama
curl -X POST "https://api.github.com/repos/$OWNER/$REPO/dispatches" \
	-H "Authorization: token $PERSONAL_TOKEN" \
	-H "Accept: application/vnd.github+json" \
	-d '{"event_type":"run-ollama-agent","client_payload":{"reason":"test"}}'
```

- I added a helper script `scripts/trigger_dispatch.sh` that will use `gh` if available or `curl` with `GITHUB_TOKEN`/`PERSONAL_TOKEN`.

Storing and using your token (quick steps)

- After creating the fine-grained token in GitHub, store it as a repository secret:

	1. Go to https://github.com/scottscott/agent-ollama -> Settings -> Secrets and variables -> Actions -> New repository secret.
	2. Name it `PERSONAL_TOKEN` and paste the token value, then save.

- To run the trigger locally using that token (one-off):

```bash
# export the token into your shell for the current session
export PERSONAL_TOKEN="$PERSONAL_TOKEN"
# run the helper (script will pick up PERSONAL_TOKEN)
bash scripts/trigger_dispatch.sh
```

- To let a workflow step use the secret, reference it in the workflow step's `env`:

```yaml
env:
	PERSONAL_TOKEN: ${{ secrets.PERSONAL_TOKEN }}
run: bash scripts/trigger_dispatch.sh
```

Security note: Keep tokens in repository secrets (or GitHub's secret manager), not in plaintext files or command history. Use a fine-grained token limited to this repository where possible.

Run Ollama locally (self-hosted runner)

If you want the model to run on your local machine (so it doesn't spin up on GitHub-hosted runners), use a self-hosted runner with Ollama installed.

1. Install Ollama on your machine following https://ollama.com/docs.
2. Register a self-hosted runner for this repository: GitHub -> Settings -> Actions -> Runners -> Add runner. During registration add the label `ollama` (or edit the runner labels later).
3. On your machine, ensure the runner service is running and that Ollama can be invoked by the runner user.
4. Trigger the workflow `Ollama Agent (Self-hosted)` from the Actions tab or via `repository_dispatch`. It will run on your self-hosted runner (label `ollama`) and use the local Ollama installation.

Notes:
- The repository includes `.github/workflows/ollama-agent-selfhosted.yml` which is configured to run on `runs-on: [self-hosted, linux, ollama]`.
- Use a smaller model for quick tests (change `model: tinyllama` in the workflow) while verifying behavior.

Quick notes on safety, PR flow, and CI

- Allowlist & validation: `agent-config.json` may include an `allowlist` array of regex patterns. The runner script `scripts/execute_commands.py` supports two modes:
	- `validate` — checks agent-suggested commands against the allowlist and writes `agent_run_results.json` with the validation details.
	- `execute` — runs only the commands that match the allowlist and marks skipped commands.

- Approval-gated self-hosted run: the self-hosted workflow now separates `prepare` (run agent + validate) and `execute` (post-approval) jobs. To require manual approval create a repository `environment` named `agent-approval` (Settings → Environments) and add required reviewers or protection rules. When a run reaches the `execute` job, GitHub will pause and request approval from the configured reviewers.

- PR-based proposal workflow: instead of executing changes, the workflow `.github/workflows/ollama-agent-pr.yml` can run the agent and open a proposal PR with `AGENT_PROPOSAL.md` so humans can review and merge changes.

- CI for the repo: a CI workflow runs unit tests under `.github/workflows/ci.yml`. To run tests locally:

```bash
python3 -m unittest discover -v tests
```

If you'd like, I can open a PR from the enhancement branch with all changes, or continue iterating here on `main`.


