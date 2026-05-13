# Transfer to Server — Checklist

## What to copy

```bash
# From Mac, in the gdpval_data parent dir:
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  /Users/yangyuheng/Project/gdpval_data/ \
  user@server:/path/to/gdpval_data/
```

Total size ~10MB. Critical files included:
- `pyproject.toml` + `uv.lock` (deps)
- `.env` (API keys — verify it transferred)
- `pipeline/` (all source code)
- `scripts/` (helper scripts)
- `data/gdpval_reference/tasks.jsonl` (220 real GDPval tasks)
- `data/embeddings/gdpval_reference.npy` (cached embeddings)
- `pipeline/seeds/store/{lawyer,financial_analyst,software_engineer}/*.json` (121 seeds)
- `HANDOFF.md` (instructions for the server-side Claude)

## What NOT to copy

- `data/_archive_run_n12/` — old test data, useless
- `data/candidates/`, `data/accepted/`, `data/rejected/` — empty anyway
- `.venv/` — server will create its own

## Server setup

```bash
cd /path/to/gdpval_data

# Install uv if not already (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync deps
uv sync

# Verify env loads
uv run python -c "from pipeline.config import settings; print('OK:', settings().generator_model)"
```

## Start a new Claude Code session on the server

```bash
cd /path/to/gdpval_data
claude --dangerously-skip-permissions
```

(Note: this skips ALL permission prompts. Use because you're going to leave it unattended.)

In the new session, paste:

```
Read HANDOFF.md and execute the TODO list autonomously. The user is offline.
Use caffeinate equivalent (tmux/screen + nohup) for long-running batches.
Surface concise progress updates only.
```

## Things to verify before leaving

- [ ] `nvidia-smi` shows the A6000 free
- [ ] `df -h` shows >50GB free for model checkpoints
- [ ] `tmux` or `screen` available so the Claude session itself survives SSH disconnect
- [ ] `.env` keys transferred and load correctly
