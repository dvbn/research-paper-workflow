# Research Paper Workflow Architect

A meta-prompt for Claude Code that analyzes a research project's raw materials, researches best practices, and produces a comprehensive implementation report for building an AI-assisted academic paper writing workflow.

## What this is

This is a **two-stage system**:

1. **Stage 1 (this repo):** `RESEARCH_WORKFLOW_ARCHITECT.md` is a meta-prompt that, when run with Claude Code, deeply analyzes your research project and produces `IMPLEMENTATION_REPORT.md` — a complete blueprint.
2. **Stage 2 (guided by the report):** Build the actual paper-writing workflow from the blueprint.

## Who this is for

Researchers who write theory + applied papers with mathematical proofs, estimator derivations, and empirical data analysis. Designed for econometrics but adaptable to any quantitative field.

## Quick start

```bash
mkdir -p paper_workspace && cd paper_workspace

# Create the input structure
mkdir -p raw/{reference,style,objective,draft}

# Populate:
# raw/reference/   — Literature PDFs, textbooks
# raw/style/       — Your own published papers (for voice matching)
# raw/objective/   — Target journal papers (quality bar)
# raw/draft/       — Current notes, partial derivations (.pdf or .tex)
# raw/template.tex — LaTeX formatting template (optional)

# Optionally create config.yaml (see RESEARCH_WORKFLOW_ARCHITECT.md Section 2)

# Run the architect
claude --dangerously-skip-permissions --max-turns 500 \
  -p "$(cat ~/RESEARCH_WORKFLOW_ARCHITECT.md)"
```

**Output:** `IMPLEMENTATION_REPORT.md` in the current directory.

## What the architect does

1. **Analyzes** your raw materials (PDFs, .tex files, notes)
2. **Researches** best practices for AI-assisted academic writing (web search)
3. **Designs** a 10-phase paper production workflow:
   - PDF processing pipeline (adapted from ta-llm)
   - Multi-phase planning with adversarial critique (Claude + Codex)
   - Triple math verification (SymPy + Codex + Claude)
   - Style matching to your published voice
   - LaTeX compilation and output
4. **Produces** a detailed implementation report

## Key features

- **Triple math verification:** SymPy (algebra) + Codex (logic) + Claude (structure)
- **Style matching:** Formal style profile with anti-AI-detection checklist
- **Adversarial verification:** Codex CLI as an independent critic (different model family)
- **Adapted PDF pipeline:** Marker-PDF extraction with LaTeX equation cleanup
- **Fully autonomous:** No questions asked, graceful degradation on failures

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Optional: [Codex CLI](https://github.com/openai/codex) for adversarial verification
- Optional: [tectonic](https://tectonic-typesetting.github.io/) for LaTeX compilation

## License

MIT
