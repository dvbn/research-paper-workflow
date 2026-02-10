# Research Paper Workflow Architect

A meta-prompt for Claude Code that analyzes a research project's raw materials,
researches best practices, and produces a comprehensive implementation report
for building an AI-assisted academic paper writing workflow.

## What this is

A **two-stage system**:

1. **Stage 1 (this repo):** `RESEARCH_WORKFLOW_ARCHITECT.md` is a meta-prompt
   that, when run with Claude Code, deeply analyzes your research project and
   produces `IMPLEMENTATION_REPORT.md` — a complete blueprint.
2. **Stage 2 (guided by the report):** Build the actual paper-writing workflow
   from the blueprint.

## Who this is for

Researchers who write theory + applied papers with mathematical proofs,
estimator derivations, and empirical data analysis. Designed for econometrics
but adaptable to any quantitative field.

---

## Complete Setup Guide (from scratch)

### Step 0: Install prerequisites

```bash
# 1. Claude Code CLI (required)
# Follow: https://docs.anthropic.com/en/docs/claude-code
npm install -g @anthropic-ai/claude-code

# 2. Codex CLI (recommended — enables adversarial verification)
# Follow: https://github.com/openai/codex
npm install -g @openai/codex

# 3. tectonic (recommended — lightweight LaTeX compiler, ~50MB vs 5GB MacTeX)
brew install tectonic  # macOS
# or: cargo install tectonic

# 4. Python packages (will be installed by the workflow, but you can pre-install)
pip install sympy latex2sympy2 marker-pdf pymupdf rich pyyaml

# 5. tmux (required for overnight runs)
brew install tmux  # macOS
# or: sudo apt install tmux  # Linux
```

### Step 1: Create a project workspace

For each paper, create a **separate** workspace directory. The architect prompt
runs inside this directory and writes all output here.

```bash
# Example: a new paper on sparse GMM
mkdir -p ~/papers/sparse-gmm && cd ~/papers/sparse-gmm

# Create the input folder structure
mkdir -p raw/{reference,style,objective,draft}
mkdir -p cleaned workspace logs output
```

### Step 2: Populate the raw/ folders

| Folder | What goes here | Purpose |
|--------|---------------|---------|
| `raw/draft/` | Your current working paper (.pdf or .tex) — notes, partial derivations, any state of the draft | The paper being written |
| `raw/reference/` | Literature PDFs + **textbooks/handbook chapters** used for proofs | Citation source + proof verification ground truth |
| `raw/style/` | 2-4 of YOUR published papers | Voice/style matching (sentence length, citation patterns, phrasing) |
| `raw/objective/` | 2-3 recent papers from the TARGET JOURNAL | Quality bar — structure, length, proof density, formatting |
| `raw/template.tex` | LaTeX formatting template (optional) | Formatting skeleton for the output paper |

**Important for theory papers:** Put all math/stat textbooks and handbook
chapters in `raw/reference/`. The workflow extracts theorem statements verbatim
and uses them as ground truth for proof verification. The more reference material
you provide, the more rigorous the verification.

Example reference/ contents for an econometric theory paper:
```
raw/reference/
├── vanderVaart1998_AsymptoticStatistics.pdf
├── Wainwright2019_HighDimStats.pdf
├── BuhlmannVanDeGeer2011_StatsHighDimData.pdf
├── HornJohnson2013_MatrixAnalysis.pdf
├── Billingsley1995_ProbabilityAndMeasure.pdf
├── NeweyMcFadden1994_LargeSampleEstimation.pdf    # handbook chapter
├── CarrascoFlorensRenault2007_LinearInverse.pdf    # handbook chapter
├── Friedman2008_GraphicalLasso.pdf                 # key method paper
├── CaiLiuZhou2016_SparsePrecision.pdf              # key theory paper
└── ... (all 20+ papers for the literature)
```

### Step 3: (Optional) Create config.yaml

The workflow works without any config — it infers everything from the raw/
contents. But you can override defaults:

```yaml
# config.yaml (all fields optional)
paper:
  title: "Adaptive Sparse GMM via Robust Graphical Models"
  target_journal: "Journal of Econometrics"
  authors: ["David Benatia"]

workflow:
  log_level: standard        # minimal | standard | verbose
  codex_enabled: true        # set false if Codex CLI not installed
  sympy_verify: true
  proof_comment_level: detailed  # minimal | standard | detailed
  max_reconciliation_rounds: 3

# No need to list papers — the workflow reads raw/ automatically
```

### Step 4: Copy the architect prompt

```bash
# Copy the meta-prompt to a stable location (once)
cp /path/to/RESEARCH_WORKFLOW_ARCHITECT.md ~/RESEARCH_WORKFLOW_ARCHITECT.md

# Or clone this repo
git clone https://github.com/dvbn/research-paper-workflow.git
```

### Step 5: Run the architect

**This will run for 2-4 hours. Use tmux so it survives terminal disconnects.**

```bash
# Start a tmux session
tmux new -s paper

# Prevent macOS sleep (important for overnight runs)
caffeinate -dims &

# Navigate to project workspace
cd ~/papers/sparse-gmm

# Run the architect
claude --dangerously-skip-permissions --max-turns 500 \
  -p "$(cat ~/RESEARCH_WORKFLOW_ARCHITECT.md)" 2>&1 | tee run.log

# DETACH from tmux (keeps it running): press Ctrl-B then D
# REATTACH later: tmux attach -t paper
```

### Step 6: Monitor progress

While the workflow runs (in another terminal):

```bash
# Watch live progress
tail -f ~/papers/sparse-gmm/workspace/progress.jsonl

# Check which phase is running
cat ~/papers/sparse-gmm/workspace/checkpoint.json

# Watch the full log
tail -f ~/papers/sparse-gmm/run.log
```

### Step 7: If interrupted — restart

The workflow saves checkpoints after each phase. If it gets killed (machine
sleep, OOM, Claude hits max turns), just re-run the same command:

```bash
# Reattach to tmux
tmux attach -t paper

# Re-run — it will detect the checkpoint and resume
cd ~/papers/sparse-gmm
claude --dangerously-skip-permissions --max-turns 500 \
  -p "$(cat ~/RESEARCH_WORKFLOW_ARCHITECT.md)" 2>&1 | tee -a run.log
```

The workflow checks `workspace/checkpoint.json` at startup and skips completed
phases. It verifies that artifacts from completed phases still exist before
skipping.

### Step 8: Collect the output

When complete, the main output is:

```
~/papers/sparse-gmm/
├── IMPLEMENTATION_REPORT.md    # <-- THE DELIVERABLE: full blueprint
├── workspace/
│   ├── checkpoint.json         # Phase completion status
│   ├── progress.jsonl          # Timestamped progress log
│   ├── session_config.json     # System info + config
│   ├── context_analysis.json   # Research context analysis
│   ├── paper_profile.json      # Draft structure + theorem inventory
│   ├── reference_map.json      # Literature map
│   ├── textbook_theorem_index.json  # Extracted theorems from textbooks
│   ├── style_profile.json      # Writing style profile
│   ├── quality_bar.json        # Target journal standards
│   ├── research_plan.md        # Proposed paper structure
│   ├── final_plan.md           # Plan after adversarial critique
│   └── simulation_design.md    # Monte Carlo design
├── logs/
│   └── summary.md              # Human-readable run summary
└── run.log                     # Full Claude output log
```

---

## Using this for a new project

1. Create a new workspace directory: `mkdir -p ~/papers/my-new-paper`
2. Create `raw/` subfolders and populate them
3. Run the architect in tmux (same command, different directory)
4. Each project is fully self-contained — nothing is shared between projects

---

## Key features

- **Quintuple math verification:** Textbook ground-truth + SymPy (algebra) +
  Codex adversarial review + Codex independent proof check + Claude reconciliation
- **Anti-hallucination for proofs:** Every textbook citation is verified against
  the actual source PDF — theorem numbers, statements, and conditions
- **Style matching:** Formal style profile with anti-AI-detection checklist
- **Adversarial verification:** Codex CLI as independent critic (different model family)
- **Checkpoint/restart:** Survives interruptions; resumes from last completed phase
- **Live progress monitoring:** `tail -f workspace/progress.jsonl`
- **Fully autonomous:** No questions asked, graceful degradation on failures

---

## Troubleshooting

**Process killed overnight:**
Ensure you're using `tmux` + `caffeinate`. Re-run the same command — it resumes
from the checkpoint.

**Claude hits max turns (500):**
Re-run with a higher limit: `--max-turns 1000`. The checkpoint ensures no work
is repeated.

**Codex not available:**
The workflow degrades gracefully — it documents which verification steps were
skipped. Set `codex_enabled: false` in config.yaml to suppress warnings.

**PDF extraction fails for a textbook:**
The workflow falls back to pymupdf, then raw text. For textbooks with complex
math formatting, consider providing .tex source if available.

**Not enough RAM for large PDFs:**
Close other applications. The workflow processes one PDF at a time. 16GB RAM
is sufficient; 32GB is comfortable.

---

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (required)
- [Codex CLI](https://github.com/openai/codex) (recommended — adversarial verification)
- [tectonic](https://tectonic-typesetting.github.io/) (recommended — LaTeX compilation)
- Python 3.11+ with pip
- tmux (for overnight runs)
- macOS or Linux

## License

MIT
