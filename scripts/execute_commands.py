#!/usr/bin/env python3
import json
import os
import subprocess
import sys


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main(config_path, response_path):
    try:
        config = load_json(config_path)
    except Exception as e:
        print(json.dumps({"ok": False, "reason": f"Failed to load config: {e}"}))
        return

    try:
        response_text = open(response_path, 'r', encoding='utf-8').read()
        agent_resp = json.loads(response_text)
    except Exception:
        # If agent response is not valid JSON, fall back to empty
        agent_resp = {}

    commands = []
    if isinstance(agent_resp.get('commands'), list) and agent_resp.get('ok', False):
        commands = agent_resp['commands']
    else:
        commands = config.get('commands', [])

    working_dir = config.get('working_dir', '.')
    results = []

    for cmd in commands:
        try:
            proc = subprocess.run(cmd, shell=True, cwd=working_dir, capture_output=True, text=True)
            results.append({
                'command': cmd,
                'returncode': proc.returncode,
                'stdout': proc.stdout,
                'stderr': proc.stderr
            })
        except Exception as e:
            results.append({'command': cmd, 'error': str(e)})

    summary = {
        'ok': all((r.get('returncode', 0) == 0) for r in results),
        'results': results
    }

    out = json.dumps(summary, indent=2)
    print(out)
    try:
        with open('agent_run_results.json', 'w', encoding='utf-8') as f:
            f.write(out)
    except Exception:
        pass


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: execute_commands.py <config.json> <agent_response.json>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
