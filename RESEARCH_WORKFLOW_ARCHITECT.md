# Research Paper Workflow Architect — Master Orchestration Prompt

## How to use

```bash
mkdir -p paper_workspace && cd paper_workspace
# Populate raw/ folders with PDFs and .tex files
# Optionally create config.yaml with project settings
claude --dangerously-skip-permissions --max-turns 500 \
  -p "$(cat ~/RESEARCH_WORKFLOW_ARCHITECT.md)"
```

---

## Section 1: Role & Mission

You are a **research workflow architect**, not a paper writer. Your mission is to
analyze a research project's raw materials, research best practices for AI-assisted
academic writing, design a comprehensive 10-phase paper-production workflow, and
produce a detailed implementation report.

You operate **fully autonomously** — the user is asleep. Do NOT ask any questions.
Make all decisions yourself. If something fails, try alternatives. Log everything.

**What you produce:** a single file `IMPLEMENTATION_REPORT.md` in the current
directory — a complete blueprint for building the paper-writing workflow as a
reusable system.

**What you do NOT produce:** You do not write the paper. You do not produce LaTeX.
You analyze, research, design, and document.

**Target user:** An econometrics professor who writes theory + applied papers with
mathematical proofs, estimator derivations, and empirical data analysis. The workflow
must handle: theorem/proof environments, symbolic math verification, econometric
notation, BibTeX bibliography management, and style matching to the professor's
existing published voice.

---

## Section 2: Expected Inputs

The current directory should contain:

```
project_root/                   (this is paper_workspace/)
├── raw/
│   ├── reference/              # Literature PDFs, textbooks, related papers
│   ├── style/                  # User's own published papers (writing voice)
│   ├── objective/              # Target journal papers (quality and format bar)
│   ├── draft/                  # Current notes, partial derivations (.pdf or .tex)
│   └── template.tex            # LaTeX formatting template for the paper
├── cleaned/                    # (may exist from a previous run — preprocessed docs)
├── config.yaml                 # (optional) project settings
└── workspace/                  # (created by this prompt — all intermediate files)
```

### config.yaml schema (all fields optional, sensible defaults applied)

```yaml
# Project metadata
paper_title: "Asymptotic Properties of the Penalized GMM Estimator"
target_journal: "Econometrica"
co_authors: ["Jane Doe", "John Smith"]
language: "en"                    # en | fr

# Workflow options
log_level: "standard"             # minimal | standard | verbose
use_codex: true                   # Enable Codex adversarial verification
codex_max_retries: 1              # Retries per Codex invocation
max_critique_loops: 3             # Plan critique iterations
max_style_loops: 3                # Style-matching revision loops per section

# Math verification
sympy_verify: true                # Enable SymPy proof verification
proof_comment_level: "detailed"   # minimal | standard | detailed

# LaTeX
latex_compiler: "tectonic"        # tectonic | latexmk | pdflatex
bibliography_style: "econometrica"

# Time budget (minutes)
max_analysis_time: 60
max_research_time: 45
max_design_time: 120
max_total_time: 240               # 4 hours total
```

**Defaults:** If `config.yaml` is absent, use these defaults:
- `log_level`: standard
- `use_codex`: true (but gracefully degrade if codex CLI unavailable)
- `max_critique_loops`: 3
- `max_style_loops`: 3
- `sympy_verify`: true
- `latex_compiler`: tectonic
- `max_total_time`: 240 minutes
- All other fields: inferred from raw/ contents

---

## Section 3: Analysis Phase — Understand the Research Context

### 3A. Startup checks

Before doing anything else:

1. **Create workspace/**:
   ```bash
   mkdir -p workspace cleaned
   ```

2. **Log system info** to `workspace/session_config.json`:
   ```json
   {
     "timestamp": "ISO-8601",
     "python_version": "output of python3 --version",
     "available_tools": {
       "codex": "boolean — check with: which codex",
       "tectonic": "boolean — check with: which tectonic",
       "latexmk": "boolean — check with: which latexmk",
       "marker": "boolean — check with: python3 -c 'import marker'",
       "sympy": "boolean — check with: python3 -c 'import sympy'"
     },
     "disk_free_gb": "df -h . parsed",
     "cpu_count": "nproc or sysctl",
     "ram_gb": "sysctl hw.memsize or /proc/meminfo"
   }
   ```

3. **Read config.yaml** if present. Merge with defaults. Write merged config to
   `workspace/session_config.json` (append to the system info).

4. **Inventory raw/ contents**:
   - Count files per subfolder (reference, style, objective, draft)
   - List file names and sizes
   - Check if `raw/template.tex` exists
   - Check if `cleaned/` already has processed files
   - Write inventory to `workspace/raw_inventory.json`

5. **Set log level** from config (or default to standard).

### 3B. Document processing (raw/ → cleaned/)

If `cleaned/` already contains files from a previous run, skip extraction and use
those. Otherwise, process raw/ PDFs and .tex files.

**For PDF files — adapt the ta-llm extraction pipeline:**

1. **Install dependencies** (in a workspace venv if possible):
   ```bash
   python3 -m venv workspace/.venv 2>/dev/null || true
   source workspace/.venv/bin/activate 2>/dev/null || true
   pip install marker-pdf pymupdf pyyaml rich 2>/dev/null || true
   ```

2. **Extract with Marker-PDF** (preferred) or PyMuPDF (fallback):
   - Convert each PDF to Markdown
   - Preserve LaTeX equations where possible
   - Handle multi-column layouts
   - For documents >30 pages, extract chapter-by-chapter using TOC detection

3. **Apply regex LaTeX fixes** (adapted from ta-llm `regex_latex_fix.py`):
   - Fix TeX font encoding artifacts:
     ```
     ð → (    Þ → )    þ → +    ¤ → ff    ‰ → ffi    ½ → [    ¼ → =
     ```
   - Wrap lone LaTeX commands (`\alpha`, `\beta`, `\hat`, `\sum`, etc.) in `$...$`
   - Wrap math operators (`E(...)`, `Var(...)`, `Cov(...)`, `plim`, etc.) in `$...$`
   - Fix convergence arrows: `+d` → `$\xrightarrow{d}$`, `+p` → `$\xrightarrow{p}$`
   - Detect math regions (`$$...$$`, `$...$`, `\[...\]`) and avoid modifying them
   - Skip code blocks and YAML front matter

4. **Verify equation quality** (adapted from ta-llm `verify_equations.py`):
   - Count LaTeX equations, raw math patterns, garbled patterns
   - Quality score per file (0-100): garbled = -5 pts each, raw = -2 pts each
   - Log quality report to `workspace/extraction_quality.json`
   - Flag files with quality < 80 for manual review

5. **Write cleaned files** to `cleaned/` with YAML front matter:
   ```yaml
   ---
   source_file: "raw/reference/hansen2022.pdf"
   source_type: "reference"
   extraction_method: "marker"
   extraction_quality: 92
   page_count: 45
   title: "Econometrics"
   authors: ["Bruce Hansen"]
   ---
   ```

**For .tex files** (common in draft/):
- Read directly — no extraction needed
- Parse `\title{}`, `\author{}`, `\begin{theorem}`, `\begin{proof}`, etc.
- Copy to cleaned/ with appropriate front matter
- These are already in the target format — preserve exactly

### 3C. Build context analysis

Read all cleaned documents. Build `workspace/context_analysis.json`:

```json
{
  "research_question": "Inferred from draft and notes",
  "theoretical_framework": "What mathematical/statistical framework is used",
  "current_proof_status": {
    "complete_proofs": ["Theorem 1: consistency", "Lemma 2: rate"],
    "incomplete_proofs": ["Theorem 3: asymptotic normality — missing regularity conditions"],
    "missing_proofs": ["Corollary 1 — stated without proof"]
  },
  "notation_inventory": {
    "estimators": {"\\hat{\\theta}_n": "penalized GMM estimator", "\\theta_0": "true parameter"},
    "spaces": {"\\Theta": "parameter space", "\\mathcal{H}": "Hilbert space"},
    "operators": {"\\|\\cdot\\|": "Euclidean norm", "E_n[\\cdot]": "sample average"},
    "conventions": "subscript n for sample size, 0 for true values"
  },
  "literature_landscape": {
    "foundational": ["papers the proofs build on"],
    "competing": ["alternative approaches to the same problem"],
    "empirical": ["application papers in the target domain"]
  },
  "empirical_component": {
    "data_description": "What data is used or planned",
    "estimation_method": "GMM, MLE, Bayesian, etc.",
    "software": "R, Stata, Python, MATLAB"
  },
  "target_journal_conventions": "Inferred from objective/ papers"
}
```

### 3D. Build reference profiles

**From draft/ files** — `workspace/paper_profile.json`:
- Current structure (sections, subsections)
- Which sections are written vs. outlined vs. missing
- Theorem/proposition inventory with proof status
- Notation used

**From reference/ files** — `workspace/reference_map.json`:
- For each reference: title, authors, key results, methods, how it relates to draft
- Which results are cited/used in the proofs
- Which results provide context or motivation

**From style/ files** — `workspace/style_profile.json`:
- See Section 8 for the full schema

**From objective/ files** — `workspace/quality_bar.json`:
- Paper length (pages, word count)
- Proof density (theorems per page)
- Citation count and style
- Abstract structure
- Section naming conventions
- Level of mathematical formality

---

## Section 4: Research Phase — Best Practices & Gaps

### 4A. Web research

Use web search to find recent work (2023-2026) on:

1. **AI-assisted academic writing workflows**
   - Search: "AI-assisted academic paper writing workflow 2024 2025"
   - Search: "LLM academic writing pipeline reproducible research"
   - Look for: frameworks, tools, published experiences

2. **Symbolic math verification in research**
   - Search: "SymPy proof verification academic mathematics"
   - Search: "automated theorem proving econometrics"
   - Look for: what can/cannot be verified, best practices

3. **Adversarial LLM verification**
   - Search: "adversarial LLM verification dual model checking"
   - Search: "AI model cross-checking academic correctness"
   - Look for: patterns where one model checks another's work

4. **Automated LaTeX paper production**
   - Search: "automated LaTeX paper generation from markdown"
   - Search: "tectonic LaTeX compiler workflow"
   - Look for: tools, templates, compilation pipelines

5. **Style matching and AI detection avoidance**
   - Search: "academic writing style matching LLM"
   - Search: "AI detection academic papers avoiding markers"
   - Look for: techniques to maintain authentic voice

### 4B. Gap analysis

Compare the user's reference/ folder against the literature landscape. Identify:
- Missing foundational references
- Missing recent references (last 2-3 years)
- References that would strengthen specific proofs or arguments
- Suggest up to 10 additional papers with DOI/arXiv links

### 4C. Tool and library survey

Identify the best tools for each workflow component:
- PDF extraction: Marker-PDF, PyMuPDF, Nougat, GROBID
- Math verification: SymPy, Lean 4, Mathematica (if available)
- LaTeX compilation: tectonic, latexmk, pdflatex
- Bibliography: bibtex, biblatex, crossref API
- Style analysis: textstat, spacy, custom metrics

Write findings to `workspace/research_findings.json`.

---

## Section 5: Design the 10-Phase Workflow

This is the core of the report. For each phase, the implementation report must
specify: purpose, inputs, outputs, tools used, code snippets, error handling,
time budget, and verification criteria.

### Phase 0: Environment Bootstrap

**Purpose:** Set up a reproducible Python environment with all dependencies.

**The report must specify:**
- Exact `requirements.txt` with pinned versions
- Bootstrap script (`scripts/bootstrap.sh`):
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  # Verify LaTeX compiler
  which tectonic || brew install tectonic
  # Verify Codex CLI
  which codex && echo "Codex available" || echo "Codex not available — will skip adversarial verification"
  ```
- Dependencies to install:
  - `sympy>=1.12` — symbolic math verification
  - `latex2sympy2` — parse LaTeX to SymPy expressions
  - `marker-pdf` — PDF to Markdown extraction
  - `pymupdf` — fallback PDF extraction
  - `rich` — terminal output formatting
  - `pyyaml` — configuration parsing
  - `textstat` — readability metrics for style matching
  - `bibtexparser` — BibTeX parsing
  - `requests` — API calls (CrossRef, arXiv)
- Bootstrap log: `workspace/bootstrap_log.json`

### Phase 1: Document Processing

**Purpose:** Convert raw PDFs and .tex files into structured, searchable Markdown
with clean LaTeX equations.

**The report must specify:**
- Adapted ta-llm pipeline architecture (not a copy — adapted for research papers):
  1. Marker-PDF extraction with equation preservation
  2. Regex LaTeX fix pass (font artifacts, lone commands, math operators, arrows)
  3. Equation verification with quality scoring
- Extraction quality thresholds (reject < 60, warn < 80, accept >= 80)
- Handling of .tex files (direct parsing, no extraction needed)
- Output format: YAML-frontmatter Markdown in cleaned/
- Fallback chain: Marker → PyMuPDF → raw text + manual flag
- Code snippets for each pipeline stage

### Phase 2: Ingestion & Familiarization

**Purpose:** Build structured profiles of the research project, references,
writing style, and quality target.

**The report must specify how to build each profile:**

**paper_profile.json** (from draft/):
```json
{
  "title": "...",
  "abstract": "...",
  "sections": [
    {"name": "Introduction", "status": "written", "word_count": 2100},
    {"name": "Model", "status": "outlined", "word_count": 500},
    {"name": "Asymptotic Theory", "status": "partial", "word_count": 1200}
  ],
  "theorems": [
    {
      "id": "thm:consistency",
      "statement": "\\hat{\\theta}_n \\xrightarrow{p} \\theta_0",
      "proof_status": "complete",
      "dependencies": ["assumption:A1", "assumption:A2", "lemma:uniform_lln"]
    }
  ],
  "assumptions": [...],
  "notation": {...}
}
```

**reference_map.json** (from reference/):
```json
{
  "papers": [
    {
      "id": "hansen2022",
      "title": "Econometrics",
      "authors": ["Bruce Hansen"],
      "key_results": ["Theorem 7.1: OLS consistency", "Theorem 8.3: CLT for GMM"],
      "relevance": "Foundational — provides the GMM framework we extend",
      "cited_in_draft": true
    }
  ]
}
```

**textbook_theorem_index.json** (from reference/ — textbooks and handbook chapters):

This is a critical artifact. For each textbook/handbook chapter in reference/:
1. Read the table of contents and index
2. Extract every theorem, lemma, proposition, and corollary that is potentially
   relevant to the draft's proof strategy
3. For each result, record the **exact statement** (verbatim from the source),
   the **exact location** (chapter, section, page, theorem number), and the
   **complete list of conditions/assumptions** required

```json
{
  "sources": [
    {
      "id": "vanderVaart1998",
      "title": "Asymptotic Statistics",
      "type": "textbook",
      "results": [
        {
          "id": "vdV-Thm5.9",
          "type": "theorem",
          "number": "Theorem 5.9",
          "chapter": 5,
          "page": 52,
          "name": "Consistency of M-estimators",
          "statement_verbatim": "Let M_n be random functions and ... [exact text from PDF]",
          "conditions": [
            "Compactness of parameter space",
            "Uniform convergence: sup |M_n - M| -> 0 in probability",
            "Identifiable separation: M(theta) < M(theta_0) for theta != theta_0"
          ],
          "proof_technique": "Argmax continuous mapping",
          "relevant_to": ["thm:consistency", "thm:uniform_convergence"]
        },
        {
          "id": "vdV-Thm5.21",
          "type": "theorem",
          "number": "Theorem 5.21",
          "chapter": 5,
          "page": 65,
          "name": "Asymptotic normality of Z-estimators",
          "statement_verbatim": "...",
          "conditions": ["...", "..."],
          "proof_technique": "Linearization + CLT",
          "relevant_to": ["thm:asymptotic_normality"]
        }
      ]
    },
    {
      "id": "wainwright2019",
      "title": "High-Dimensional Statistics",
      "type": "textbook",
      "results": [...]
    },
    {
      "id": "carrasco_florens_renault2007",
      "title": "Linear Inverse Problems in Structural Econometrics",
      "type": "handbook_chapter",
      "results": [...]
    }
  ]
}
```

**CRITICAL:** The `statement_verbatim` field must be copied **exactly** from the
PDF, not paraphrased. This is the ground truth against which all proof citations
will be verified. If the PDF extraction is unclear, flag it and include the page
number for human verification.

Build the index by:
1. Reading each textbook/handbook PDF in raw/reference/
2. Identifying chapters relevant to the draft's proof strategy (from paper_profile.json)
3. Extracting theorems with full statements and conditions
4. Cross-referencing with the draft's theorem inventory to build the `relevant_to` links

This index is used in Phase 7A for proof construction and in the textbook
citation verification loop.

**style_profile.json** — see Section 8 for full schema.

**quality_bar.json** (from objective/):
```json
{
  "target_journal": "Econometrica",
  "typical_paper_length": {"pages": 45, "word_count": 15000},
  "proof_density": 0.8,
  "citation_count": {"mean": 42, "range": [25, 70]},
  "abstract_length": {"words": 150, "sentences": 6},
  "section_structure": ["Introduction", "Model", "Main Results", "Monte Carlo", "Empirical Application", "Conclusion"],
  "formatting_notes": "Double-spaced, 12pt, 1-inch margins for submission"
}
```

### Phase 3: Research Planning

**Purpose:** Propose the paper structure, theorem inventory, and proof strategy.

**The report must specify:**
- How to generate a section outline with estimated lengths
- How to build a theorem/proposition inventory from draft analysis
- Proof strategy for each theorem:
  - Which technique (contradiction, induction, direct, epsilon-delta)
  - Which lemmas are needed
  - Which reference results are invoked
  - What regularity conditions are required
- Missing references identification via web search (CrossRef API, arXiv API, Google Scholar)
- Output: `workspace/research_plan.md` with:
  - Proposed section structure
  - Theorem inventory with proof strategies
  - Gap analysis (missing proofs, weak arguments, needed references)
  - Estimated effort per section

### Phase 4: Plan Evaluation (Adversarial)

**Purpose:** Use Codex CLI as an adversarial critic to stress-test the research plan.

**The report must specify the exact invocation pattern:**

```bash
# Prepare the context file for Codex
cat workspace/research_plan.md workspace/context_analysis.json > workspace/codex_input.md

# Invoke Codex for plan critique
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C "$(pwd)/workspace" \
  -o "$(pwd)/workspace/plan_review.md" \
  "You are a senior econometrician reviewing a research plan. Read codex_input.md.
   Critique the plan on these dimensions:
   1. Is the contribution genuinely novel? Compare against the cited literature.
   2. Are there theoretical gaps? Missing assumptions, incomplete proof strategies?
   3. What will journal referees object to? Anticipate the 3 most likely criticisms.
   4. Is the empirical design convincing? Sample size, identification, robustness?
   5. Suggest specific improvements with references.
   Write your critique to plan_review.md."
```

**Critique-revision loop (max 3 iterations):**
1. Claude reads `workspace/plan_review.md`
2. Claude revises `workspace/research_plan.md` addressing each critique point
3. Codex is invoked again on the revised plan
4. Repeat until convergence or max iterations reached
5. Log all iterations to `workspace/critique_log.json`

**If Codex is unavailable:**
- Claude performs self-critique using a structured rubric
- Document the gap: "Adversarial verification was single-model only"

### Phase 5: Contribution Assessment

**Purpose:** Rigorously evaluate the proposed contribution against the literature.

**The report must specify:**
- Comparison matrix: proposed results vs. closest existing results
- Novelty dimensions:
  - New estimator / new proof technique / new application / new data
  - Generalization of existing results (which assumptions relaxed?)
  - Computational innovation (new algorithm, faster convergence?)
- Significance for target journal:
  - Does it meet the journal's bar? (compare against objective/ papers)
  - What makes it publishable vs. incremental?
- Strengthening strategies if the contribution is marginal:
  - Additional theoretical results that would strengthen the paper
  - Empirical applications that would showcase the theory (propose concrete
    datasets, estimators, and specifications — Phase 7D will detail these proposals)
  - Monte Carlo designs that demonstrate finite-sample properties
  - Connections to other literatures

### Phase 6: Final Production Plan

**Purpose:** Merge the original plan, Codex critiques, and contribution assessment
into a final actionable blueprint.

**The report must specify:**
- Structure of `workspace/final_plan.md`:
  - Section-by-section writing plan with target word counts
  - Theorem-by-theorem production plan with verification strategy
  - Literature integration plan (which references go where)
  - Empirical avenues plan: proposed applications, datasets, and Monte Carlo
    designs that connect to the theory (Phase 7D will develop these proposals
    into a detailed document the user can act on)
  - Timeline with dependencies (which sections must be written first)
- Decision log: which critique points were accepted vs. rejected, and why

### Phase 7: Production (the core writing phase)

This is the largest phase. The report must provide detailed specifications for
four sub-phases.

#### Phase 7A: Mathematical Production

**Purpose:** Write and verify all theorems, lemmas, propositions, and proofs.

**The report must specify:**

1. **File organization:** Each theorem/proof in a separate .tex file:
   ```
   workspace/math/
   ├── thm_consistency.tex
   ├── proof_consistency.tex
   ├── lemma_uniform_lln.tex
   ├── proof_uniform_lln.tex
   └── ...
   ```

2. **Proof dependency mapping (before writing any proof):**

   Before writing each proof, consult `textbook_theorem_index.json` to build a
   **proof blueprint**:
   ```json
   // workspace/math/blueprint_consistency.json
   {
     "theorem": "thm:consistency",
     "proof_strategy": "M-estimation argmax + uniform LLN",
     "textbook_results_needed": [
       {
         "source": "vanderVaart1998",
         "result": "Theorem 5.9 (Consistency of M-estimators)",
         "page": 52,
         "conditions_to_verify": [
           "Compactness of parameter space → established in Assumption A1",
           "Uniform convergence → proved in Lemma 2 using Wainwright Thm 6.2",
           "Identifiable separation → established in Assumption A3"
         ]
       },
       {
         "source": "wainwright2019",
         "result": "Theorem 6.2 (Uniform convergence via covering numbers)",
         "page": 168,
         "conditions_to_verify": [
           "Sub-Gaussian increments → follows from bounded moment conditions"
         ]
       }
     ],
     "condition_gap_check": "All conditions traceable to paper's assumptions"
   }
   ```

3. **Quintuple verification protocol for each proof:**

   **Layer 1 — Claude writes the proof (textbook-grounded):**
   - Consult the proof blueprint; cite textbook results **by exact theorem number**
   - Every non-obvious step annotated with its source:
     `% Step 3: By Theorem 5.9 of van der Vaart (1998, p. 52), consistency follows`
     `% from (i) compactness (Assumption A1), (ii) uniform convergence (Lemma 2),`
     `% and (iii) identifiable separation (Assumption A3).`
   - Regularity conditions explicitly invoked at each step
   - Comment level controlled by `proof_comment_level` in config
   - **Rule:** "By standard arguments" is NEVER acceptable. Every step must name
     its source or be self-contained within the proof.

   **Layer 2 — Textbook citation ground-truth verification:**

   This is the **anti-hallucination layer**. LLMs can confidently cite a theorem
   that doesn't exist, misstate its conditions, or apply it where it doesn't apply.
   This step catches all such errors.

   For each textbook/handbook citation in the proof:
   a. **Re-read the actual source:** Open the PDF of the cited textbook and read
      the exact page/theorem cited. Extract the verbatim statement.
   b. **Statement match:** Compare what the proof claims the theorem says vs what
      it actually says. Flag any mismatch (wrong theorem number, wrong statement,
      missing qualifications).
   c. **Condition audit:** Extract the complete list of conditions required by the
      actual theorem. For EACH condition, verify it is satisfied:
      - Trace back to a specific assumption in the paper, OR
      - Trace to a result proved earlier in the paper, OR
      - Flag as UNVERIFIED GAP
   d. **Write citation verification report:**
   ```json
   // workspace/math/citation_verify_consistency.json
   {
     "proof": "proof_consistency.tex",
     "citations_checked": [
       {
         "claimed": "Theorem 5.9 of van der Vaart (1998)",
         "actual_source_page": 52,
         "statement_match": true,
         "conditions_required": [
           {"condition": "compact parameter space", "satisfied_by": "Assumption A1", "verified": true},
           {"condition": "uniform convergence", "satisfied_by": "Lemma 2", "verified": true},
           {"condition": "identifiable separation", "satisfied_by": "Assumption A3", "verified": true}
         ],
         "status": "VERIFIED"
       },
       {
         "claimed": "Corollary 6.5 of Wainwright (2019)",
         "actual_source_page": 175,
         "statement_match": false,
         "mismatch_detail": "Proof claims Corollary 6.5 gives rate O(sqrt(log p / n)), but actual statement gives O(sqrt(s log p / n)) where s is sparsity",
         "status": "MISMATCH — must fix"
       }
     ],
     "overall_status": "NEEDS REVISION"
   }
   ```

   **CRITICAL RULE:** Never trust Claude's memory of a theorem. Always re-read
   the actual PDF source. If the PDF is unavailable or unreadable at the cited
   page, flag it for human verification — do NOT guess.

   **Layer 3 — SymPy algebraic verification:**
   ```python
   # verify_proof_consistency.py
   import sympy as sp
   from latex2sympy2 import latex2sympy

   # Define symbols
   n, theta, theta_0 = sp.symbols('n theta theta_0', positive=True)

   # Verify key algebraic steps
   # Step 1: Objective function decomposition
   Q_n = ...  # parsed from proof
   Q_0 = ...  # population objective

   # Verify: Q_n - Q_0 → 0 uniformly
   # (Document what CAN vs CANNOT be verified — see Section 7)

   # Step 2: Verify the triangle inequality application
   lhs = ...
   rhs = ...
   assert sp.simplify(rhs - lhs) >= 0, "Triangle inequality step failed"

   # Log results
   results = {
     "theorem": "consistency",
     "steps_verified": [...],
     "steps_not_verifiable": [...],
     "status": "PASS" | "FAIL" | "PARTIAL"
   }
   ```

   **Layer 4 — Codex adversarial review (logic + citations):**
   ```bash
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     -C "$(pwd)/workspace/math" \
     -o "$(pwd)/workspace/math/review_consistency.md" \
     "You are a mathematical referee with access to the cited textbooks.

      Read thm_consistency.tex, proof_consistency.tex, and
      citation_verify_consistency.json.

      Also read the following textbook excerpts (provided in workspace/textbook_excerpts/):
      - vanderVaart1998_thm5.9.txt
      - wainwright2019_thm6.2.txt

      Perform a RIGOROUS review:
      1. Is the proof logically complete? Are there gaps between steps?
      2. For each textbook citation: does the cited result ACTUALLY imply what
         the proof claims? Are ALL conditions of the cited theorem satisfied?
      3. Are the convergence arguments rigorous? Rate arguments correct?
      4. Are there issues with measurability, integrability, or uniformity?
      5. Could a skeptical referee with the cited textbook on their desk find
         any error or unjustified step?

      Be adversarial. Flag EVERYTHING that is not bulletproof.
      Write a detailed line-by-line review."
   ```

   **Layer 5 — Codex independent proof check:**

   A second Codex pass where Codex attempts to **independently verify** the
   main result using the textbook excerpts, WITHOUT seeing Claude's proof:
   ```bash
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     -C "$(pwd)/workspace/math" \
     -o "$(pwd)/workspace/math/independent_check_consistency.md" \
     "You are a mathematical economist. You have access to:
      - thm_consistency.tex (the theorem statement and assumptions)
      - Textbook excerpts in workspace/textbook_excerpts/

      WITHOUT reading proof_consistency.tex, attempt to prove the theorem
      yourself using the provided textbook results. Then compare your proof
      strategy with the one in proof_consistency.tex.

      Report:
      1. Does your proof strategy match? If not, which is stronger?
      2. Did you need any conditions not listed in the theorem's assumptions?
      3. Are there simpler or more standard ways to prove this result?
      4. Any concerns about the proof in proof_consistency.tex?"
   ```

4. **Reconciliation protocol:**
   - Compare: Claude's proof, citation verification, SymPy results, Codex
     adversarial review, and Codex independent check
   - If all agree: mark as verified
   - If citation mismatch found: fix citation, re-read source, re-verify
   - If condition gap found: either strengthen paper's assumptions or find a
     weaker textbook result that applies
   - If Codex independent check uses a different strategy: evaluate which is
     stronger and adopt the better approach
   - If disagreement on logic: Claude investigates with textbook open, fixes
     the proof, re-runs full verification pipeline
   - Max 3 reconciliation rounds per proof (increased from 2 due to citation checks)
   - Log all verification results to `workspace/math/verification_log.json`

5. **Textbook excerpt management:**

   To enable Codex (which cannot read PDFs) to verify textbook citations:
   - For each textbook result cited in any proof, extract the verbatim text
     to a plain-text file:
     `workspace/textbook_excerpts/vanderVaart1998_thm5.9.txt`
   - Include: theorem number, page, full statement, all conditions, and any
     relevant surrounding discussion (e.g., remarks about sharpness)
   - These files serve as the shared ground truth for both Claude and Codex

#### Phase 7B: Prose Production

**Purpose:** Write each section with style matching to the user's voice.

**The report must specify:**

1. **File organization:** Each section in a separate .tex file:
   ```
   workspace/sections/
   ├── 01_introduction.tex
   ├── 02_model.tex
   ├── 03_main_results.tex
   ├── 04_monte_carlo.tex
   ├── 05_empirical.tex
   ├── 06_conclusion.tex
   └── ...
   ```

2. **Style-matching feedback loop (max 3 iterations per section):**

   **Iteration 1 — Write draft:**
   - Use style_profile.json to guide voice, structure, and conventions
   - Incorporate theorems from Phase 7A
   - Cite references genuinely (discuss, don't just cite-dump)

   **Iteration 2 — Style comparison:**
   - Compare against style_profile.json metrics:
     - Sentence length distribution (mean, std, min, max)
     - Paragraph length distribution
     - Active vs. passive voice ratio
     - Hedging frequency
     - Citation integration style (narrative vs. parenthetical ratio)
   - Check for AI-writing markers (see Section 8 anti-AI checklist)
   - Generate style delta report

   **Iteration 3 — Revise:**
   - Adjust sentence lengths to match user's distribution
   - Replace formulaic structures with varied patterns
   - Add the user's distinctive phrases and constructions
   - Remove AI markers (excessive hedging, uniform structure, etc.)
   - Re-check style metrics

3. **Literature engagement rules:**
   - Never cite without discussing: every citation must serve an argumentative purpose
   - Integrate references into the narrative flow
   - Compare and contrast, don't enumerate
   - Use the user's citation style (from style_profile.json)

#### Phase 7C: Integration & Revision

**Purpose:** Combine all sections into a single paper and perform full revision.

**The report must specify:**

1. **Assembly:**
   - Combine sections into `workspace/paper.tex` using template.tex as the skeleton
   - Insert theorems, proofs, figures, tables at correct locations
   - Generate `workspace/references.bib` from all cited works
   - Verify all `\ref{}`, `\cite{}`, `\label{}` cross-references

2. **Revision pass 1 — Notation consistency:**
   - Build notation table from all sections
   - Flag inconsistencies (same symbol for different meanings, or different symbols
     for the same object)
   - Fix all notation issues
   - Verify theorem numbering is sequential

3. **Revision pass 2 — Flow and argumentation:**
   - Read the paper from start to finish
   - Check transitions between sections
   - Verify the argument builds logically
   - Check that the introduction promises what the paper delivers
   - Check that the conclusion matches the results

#### Phase 7D: Empirical Avenues & Applications Design

**Purpose:** Identify and propose empirical applications, data analyses, or
Monte Carlo designs that connect to the theoretical results. This phase does
**NOT** execute any code or run any analysis — it produces a detailed proposal
document that the user can act on later.

**The report must specify:**

1. **Scope determination (from context_analysis.json):**

   The workflow must detect which case applies:

   **Case A — Draft already contains empirical work:**
   - Map existing empirical specifications to the theoretical model: which theorem
     does each regression/test correspond to? Are the moment conditions correct?
   - Identify gaps: theoretical predictions that have no empirical counterpart
   - Propose improvements to existing analysis:
     - Additional robustness checks referees will ask for
     - Alternative specifications that better match the theory's assumptions
     - Missing standard error corrections (clustering, HAC, bootstrap)
     - Specification tests implied by the model (overidentification, Hausman, etc.)
   - Propose extensions: additional datasets, sample periods, or subgroup analyses
     that would showcase the estimator's properties

   **Case B — Draft is pure theory, no empirical component:**
   - Propose 2-3 fitting empirical applications based on the theoretical results
   - For each proposal, specify:
     - Which theoretical result it illustrates
     - Candidate datasets (public: FRED, Penn World Table, IPUMS, replication
       packages from published papers, etc.) with download URLs or DOIs
     - Estimator and specification: what to estimate, which variables, which
       instruments (if applicable)
     - Expected results: what the theory predicts the empirical exercise should find
     - Feasibility assessment: data availability, sample size, computational cost
   - Propose Monte Carlo simulation designs:
     - DGP specifications that match the model's assumptions
     - Sample sizes to illustrate finite-sample vs. asymptotic behavior
     - Comparison estimators (what should the proposed estimator beat?)
     - Metrics: bias, RMSE, size, power, coverage probability

   **Case C — Draft includes Monte Carlo simulations:**
   - Assess whether the simulation design adequately tests the theory
   - Propose improvements: additional DGPs, boundary cases, misspecification
     scenarios, power analysis, larger sample sizes
   - Suggest empirical applications that would complement the simulations

2. **Output 1: `workspace/empirical_avenues.md`** — Proposed applications

   A structured proposal for empirical applications (not code):

   ```markdown
   # Empirical Avenues and Applications

   ## Theory-to-Empirics Map
   | Theorem/Result | Empirical Implication | Current Status | Proposed Action |
   |---|---|---|---|
   | Thm 1: Consistency | Estimator converges with N | Not tested | Simulation |
   | Thm 2: Asymptotic normality | CI coverage → 95% | Partial | Improve DGP |
   | Prop 3: Efficiency gain | Beat OLS in RMSE | Not shown | Comparison |

   ## Proposed Application 1: [Title]
   - **Connection to theory:** Which result this illustrates
   - **Dataset:** Name, source, URL/DOI, key variables
   - **Specification:** Model to estimate, moment conditions, instruments
   - **Expected findings:** What the theory predicts
   - **Feasibility:** Data access, sample size, computation

   ## Proposed Application 2: [Title]
   ...

   ## Improvements to Existing Analysis (if draft has one)
   - [Specific improvement with justification]
   ...

   ## Robustness Checks Referees Will Request
   - [Check with rationale]
   ...
   ```

3. **Output 2: `workspace/simulation_design.md`** — Detailed Monte Carlo design

   This is a standalone, comprehensive simulation proposal. It must be detailed
   enough that a research assistant could implement it without additional
   guidance. The design must be grounded in (a) the paper's theoretical results
   and (b) simulation practices in comparable published papers.

   ```markdown
   # Monte Carlo Simulation Design

   ## Literature Basis
   Describe 3-5 published papers with comparable Monte Carlo exercises.
   For each: citation, what they simulate, DGP choices, sample sizes,
   metrics reported, and what we adopt or adapt from their design.

   ## Simulation Objectives
   For each theoretical result, state precisely what the simulation must
   demonstrate:
   | Result | What to show | Success criterion |
   |---|---|---|
   | Consistency (Thm 1) | Bias → 0 as n grows | Bias < 0.01 at n=5000 |
   | √n-rate (Thm 1) | Bias × √n stabilizes | Ratio stable across n |
   | Asymptotic normality (Thm 2) | CI coverage → 0.95 | Coverage in [0.93, 0.97] |
   | Efficiency (Prop 3) | RMSE < competitor | RMSE ratio < 1 for all DGPs |

   ## Data Generating Processes

   ### DGP 1: Baseline (satisfies all assumptions)
   - **Model:** Full mathematical specification
     - $Y_i = X_i'\theta_0 + \varepsilon_i$, where ...
     - Distribution of $X_i$: ...
     - Distribution of $\varepsilon_i$: ...
     - True parameter values: $\theta_0 = (...)$
   - **Why this DGP:** Matches Assumptions A1-A4 exactly; baseline for
     verifying that the estimator works under ideal conditions
   - **Reference:** Adapted from [Author (Year), Section N]

   ### DGP 2: Heavy tails
   - **Model:** Same as DGP 1 but $\varepsilon_i \sim t(5)$
   - **Why this DGP:** Tests robustness to Assumption A3 (finite moments);
     many empirical datasets exhibit heavy tails
   - **Reference:** Standard in [Author (Year)]

   ### DGP 3: Heteroskedasticity
   - **Model:** $\varepsilon_i = \sigma(X_i) \cdot u_i$ where ...
   - **Why this DGP:** Tests whether the estimator and its variance
     estimator remain valid under heteroskedasticity

   ### DGP 4: Weak instruments / weak identification (if applicable)
   - **Model:** ...
   - **Why this DGP:** Tests behavior when identification is marginal;
     first-stage F-statistic ~ 10

   ### DGP 5: Misspecification
   - **Model:** Violates Assumption A2 (e.g., omitted nonlinearity)
   - **Why this DGP:** Shows what happens when the model is wrong;
     referee will want to see this

   ### DGP 6: High-dimensional / many parameters (if relevant)
   - **Model:** p/n ratio = 0.1, 0.3, 0.5
   - **Why this DGP:** Tests finite-sample performance as dimensionality
     grows relative to sample size

   (Add or remove DGPs based on the specific theory. Every DGP must be
   justified by either the paper's assumptions or by published precedent.)

   ## Estimators to Compare
   | Estimator | Description | Why include |
   |---|---|---|
   | Proposed | The paper's estimator | Main object |
   | OLS | Ordinary least squares | Baseline comparator |
   | Standard GMM | Unpenalized GMM | Shows value of penalization |
   | Oracle | Estimator with known true model | Efficiency bound |
   | [Other] | ... | ... |

   ## Sample Sizes
   - n ∈ {100, 250, 500, 1000, 2500, 5000}
   - Justification: n=100 for finite-sample stress test; n=5000 to verify
     asymptotic behavior; intermediate values to trace convergence path
   - If the theory has a specific rate (e.g., n^{2/3}), choose n to make
     the rate visible in log-log plots

   ## Number of Replications
   - R = 2000 (standard) or R = 5000 (if confidence intervals on simulation
     metrics are needed)
   - Justification: R=2000 gives Monte Carlo standard error of ~0.005 for
     coverage probability estimates (sufficient for 2-decimal reporting)

   ## Metrics and Reporting

   ### Per-estimator, per-DGP, per-n:
   | Metric | Formula | What it shows |
   |---|---|---|
   | Bias | $\frac{1}{R}\sum_{r=1}^R (\hat\theta_r - \theta_0)$ | Centering |
   | Std Dev | $\sqrt{\frac{1}{R-1}\sum(\hat\theta_r - \bar{\hat\theta})^2}$ | Dispersion |
   | RMSE | $\sqrt{\text{Bias}^2 + \text{Var}}$ | Overall accuracy |
   | MAE | $\frac{1}{R}\sum|\hat\theta_r - \theta_0|$ | Robust accuracy |
   | Coverage (95%) | Fraction of CIs containing $\theta_0$ | Inference validity |
   | Avg CI length | Mean confidence interval width | Efficiency of inference |
   | Size (5%) | Rejection rate under H0 | Type I error control |
   | Power | Rejection rate under H1 (specific alternative) | Sensitivity |

   ### Reporting format:
   - **Table 1:** Bias and RMSE across n, one panel per DGP
   - **Table 2:** Coverage and average CI length across n
   - **Table 3:** Size and power (if testing is relevant)
   - **Figure 1:** Bias × √n vs. n (should flatten if √n-consistent)
   - **Figure 2:** QQ-plot of $\sqrt{n}(\hat\theta - \theta_0)/\hat\sigma$
     vs. N(0,1) for selected (n, DGP) combinations
   - **Figure 3:** Kernel density of estimator distribution overlaid with
     asymptotic normal, for selected n values
   - **Figure 4:** RMSE ratio (proposed/competitor) across n and DGPs

   ## Computational Notes
   - Estimated runtime per (DGP, n, R=2000) combination
   - Parallelization strategy (embarrassingly parallel across replications)
   - Random seed protocol for reproducibility
   - Language recommendation (Python/R/Julia) based on available packages
   ```

   **How to build this design:**
   - Start from the paper's theorems: each theorem implies a specific simulation
     objective and success criterion
   - Search the literature for published Monte Carlo designs in comparable papers
     (same estimator class, same asymptotic framework)
   - Adopt standard DGPs from those papers as baselines, then add DGPs that
     specifically test the paper's novel assumptions or results
   - Every design choice (DGP, sample size, metric) must cite either a theorem
     from the paper or a precedent from the literature

4. **Codex review of proposals:**
   ```bash
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     -C "$(pwd)/workspace" \
     -o "$(pwd)/workspace/empirical_review.md" \
     "Read simulation_design.md, empirical_avenues.md, and context_analysis.json.
      Review:
      1. Do the DGPs adequately test each theoretical result?
      2. Are there missing DGPs a referee would expect (misspecification, boundary cases)?
      3. Are the metrics and sample sizes standard for this literature?
      4. Do the proposed empirical applications correctly operationalize the theory?
      5. Are the suggested datasets appropriate and accessible?
      6. What would a referee's first objection be to this simulation design?"
   ```

5. **Web search for simulation precedents:**
   - Search for Monte Carlo designs in papers using the same estimator class
   - Search for simulation studies in the target journal (recent 3 years)
   - Identify standard DGP choices and reporting conventions in the field
   - Add findings and citations to `workspace/simulation_design.md`

### Phase 8: Adversarial Verification

**Purpose:** Final adversarial audit of the complete paper.

**The report must specify four verification passes:**

1. **Codex mathematical audit (with textbook cross-reference):**
   ```bash
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     -C "$(pwd)/workspace" \
     -o "$(pwd)/workspace/math_audit.md" \
     "Read paper.tex and all files in workspace/textbook_excerpts/.

      Perform a complete mathematical audit:
      1. Verify every proof step-by-step
      2. Check all assumptions are stated and invoked correctly
      3. Flag any logical gaps or unjustified claims
      4. Verify convergence rates and order of magnitude arguments
      5. Check that conditions in theorems are both necessary and sufficient
         (or flag if only sufficient)
      6. FOR EACH TEXTBOOK CITATION in the proofs: read the corresponding
         excerpt in textbook_excerpts/ and verify that:
         (a) The cited result is stated correctly in the paper
         (b) ALL conditions of the cited result are satisfied by the paper's
             assumptions or previously proved results
         (c) The cited result actually implies what the proof claims
      7. Flag any citation where the textbook result is misquoted, applied
         with insufficient conditions, or used in a context it was not
         designed for"
   ```

2. **Claude textbook citation re-verification (full paper sweep):**
   - Re-read every textbook/handbook citation in the final paper.tex
   - For each citation, re-open the actual PDF at the cited page
   - Verify statement match, condition satisfaction, and correct application
   - This is a FINAL CHECK independent of the per-proof checks in Phase 7A
   - Write `workspace/final_citation_audit.json` with pass/fail per citation
   - **Rule:** Any citation that cannot be verified against the source PDF
     must be flagged for human review — never leave an unverified citation

3. **Claude claim verification:**
   - For each cited result: is the citation accurate?
   - For each empirical claim: is it supported by the data/tables?
   - For each "well-known" assertion: verify with web search

3. **Codex internal consistency check:**
   ```bash
   codex exec \
     --dangerously-bypass-approvals-and-sandbox \
     --skip-git-repo-check \
     -C "$(pwd)/workspace" \
     -o "$(pwd)/workspace/consistency_audit.md" \
     "Read paper.tex. Check internal consistency:
      1. Is notation used consistently throughout?
      2. Do theorem numbers match cross-references?
      3. Are all symbols in proofs defined in the model section?
      4. Do table/figure references point to correct objects?
      5. Is the bibliography complete (every \\cite has a \\bibitem)?"
   ```

4. **Claude style audit:**
   - Compare final paper against style_profile.json
   - Run anti-AI-detection checklist (Section 8)
   - Flag sections that still sound generated

5. **Reconciliation:**
   - Merge all audit findings
   - Fix all confirmed issues
   - Document unresolved issues with justification
   - Write `workspace/verification_report.json`

### Phase 9: LaTeX Output

**Purpose:** Compile the final paper to PDF.

**The report must specify:**

1. **Template integration:**
   - Use `raw/template.tex` as the formatting base
   - If template.tex is missing, use a standard journal template (Econometrica, AER, etc.)
   - Improve the template if needed (add missing packages, fix formatting issues)
   - Do NOT change the template's visual style — only add necessary functionality

2. **File assembly:**
   ```
   output/
   ├── paper.tex         # Main file
   ├── references.bib    # Bibliography
   ├── figures/           # Generated figures (if any)
   ├── tables/            # Generated tables (if any)
   └── paper.pdf          # Compiled output
   ```

3. **Compilation chain:**
   ```bash
   # Primary: tectonic (lightweight, auto-downloads packages)
   tectonic output/paper.tex

   # Fallback 1: latexmk
   latexmk -pdf -interaction=nonstopmode output/paper.tex

   # Fallback 2: pdflatex + bibtex (manual cycle)
   cd output && pdflatex paper.tex && bibtex paper && pdflatex paper.tex && pdflatex paper.tex

   # Fallback 3: weasyprint for HTML→PDF (last resort)
   # Convert .tex to HTML via pandoc, then weasyprint
   ```

4. **Verification:**
   - Read the compiled PDF and check:
     - All theorems render correctly
     - All equations compile
     - Bibliography is complete
     - Cross-references resolve
     - No overfull hboxes (or within acceptable limits)

### Phase 10: Logging

**Purpose:** Maintain structured logs throughout the workflow.

**The report must specify:**

1. **Log levels:**
   - `minimal`: phase start/end timestamps, final status
   - `standard` (default): + per-step status, warnings, verification results
   - `verbose`: + full tool outputs, intermediate file contents, token counts

2. **Log structure:**
   ```
   logs/
   ├── summary.md              # Human-readable summary
   ├── phase_0_bootstrap.json
   ├── phase_1_extraction.json
   ├── phase_2_ingestion.json
   ├── phase_3_planning.json
   ├── phase_4_critique.json
   ├── phase_5_contribution.json
   ├── phase_6_final_plan.json
   ├── phase_7a_math.json
   ├── phase_7b_prose.json
   ├── phase_7c_integration.json
   ├── phase_7d_empirical.json
   ├── phase_8_verification.json
   ├── phase_9_latex.json
   └── token_usage.json
   ```

3. **Per-phase log schema:**
   ```json
   {
     "phase": "7a",
     "name": "Mathematical Production",
     "started_at": "ISO-8601",
     "completed_at": "ISO-8601",
     "duration_minutes": 45,
     "status": "completed",
     "steps": [
       {
         "step": "Write proof of Theorem 1",
         "status": "completed",
         "verification": {
           "sympy": "PASS",
           "codex": "PASS with 2 minor suggestions",
           "reconciled": true
         }
       }
     ],
     "warnings": [],
     "errors": [],
     "token_estimate": {
       "input_tokens": 50000,
       "output_tokens": 15000
     }
   }
   ```

4. **Summary log** (`logs/summary.md`):
   - Total runtime
   - Phase-by-phase status table
   - Verification results summary
   - Unresolved issues
   - Token usage estimates
   - Recommendations for the user

---

## Section 6: Claude-Codex Integration Protocol

### Invocation pattern

Every Codex invocation must use this exact pattern:

```bash
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C "/absolute/path/to/workspace" \
  -o "/absolute/path/to/output_file.md" \
  "PROMPT_STRING"
```

**Critical flags:**
- `--dangerously-bypass-approvals-and-sandbox` — required for autonomous execution
- `--skip-git-repo-check` — workspace may not be a git repo
- `-C` — must be an absolute path to the working directory
- `-o` — must be an absolute path to the output file

### When to invoke Codex

| Checkpoint | Phase | Purpose |
|---|---|---|
| Plan critique | 4 | Stress-test research plan |
| Proof review | 7A | Adversarial math verification per theorem |
| Full math audit | 8 | Complete paper mathematical audit |
| Consistency check | 8 | Notation, references, definitions |

### Communication protocol

Claude and Codex communicate exclusively via shared files in `workspace/`:
- Claude writes input files (context, prompts, artifacts)
- Codex reads inputs and writes output files
- Claude reads Codex outputs and incorporates feedback
- No direct API calls between models

### Failure handling

```python
import subprocess
import json

def invoke_codex(working_dir, output_file, prompt, max_retries=1):
    """Invoke Codex CLI with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                [
                    "codex", "exec",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "--skip-git-repo-check",
                    "-C", str(working_dir),
                    "-o", str(output_file),
                    prompt
                ],
                capture_output=True,
                text=True,
                timeout=300  # 5-minute timeout per invocation
            )
            if result.returncode == 0 and output_file.exists():
                return {"status": "success", "output": output_file.read_text()}
            else:
                log_warning(f"Codex attempt {attempt + 1} failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            log_warning(f"Codex attempt {attempt + 1} timed out")
        except FileNotFoundError:
            log_warning("Codex CLI not found — skipping adversarial verification")
            return {"status": "unavailable", "output": None}

    # All retries exhausted
    return {"status": "failed", "output": None}
```

**Degradation strategy:**
- If Codex fails: Claude performs self-critique using a structured rubric
- Document the gap in the verification report
- Never block the workflow on Codex availability

---

## Section 7: Math Verification Pipeline

### What CAN be verified with SymPy

| Category | Examples | SymPy capability |
|---|---|---|
| Algebraic identity | $(A+B)^{-1} = A^{-1} - A^{-1}B(I+A^{-1}B)^{-1}A^{-1}$ | Full verification |
| Derivative computation | $\frac{\partial}{\partial \theta} \log L(\theta)$ | Full verification |
| Limit evaluation | $\lim_{n\to\infty} n^{-1}\sum_{i=1}^n X_i$ | Symbolic limits |
| Matrix operations | $\text{tr}(AB) = \text{tr}(BA)$ | Full verification |
| Taylor expansion | $f(\theta) \approx f(\theta_0) + f'(\theta_0)(\theta-\theta_0)$ | Full verification |
| Distribution moments | $E[X^2]$ for known distributions | Full verification |
| Characteristic functions | $\phi_X(t) = E[e^{itX}]$ | Full verification |

### What CANNOT be verified with SymPy (require Codex or human)

| Category | Examples | Why not |
|---|---|---|
| Convergence in probability | $\hat\theta_n \xrightarrow{p} \theta_0$ | Requires probabilistic reasoning |
| Uniform convergence | $\sup_\theta |Q_n(\theta) - Q(\theta)| \to 0$ | Requires functional analysis |
| Regularity conditions | "Assumption A3 implies integrability" | Domain-specific knowledge |
| Measure-theoretic arguments | Measurability, sigma-algebra containment | Not SymPy's domain |
| Asymptotic normality | $\sqrt{n}(\hat\theta - \theta_0) \xrightarrow{d} N(0, V)$ | Requires CLT-type reasoning |
| Identification arguments | "The model is identified if..." | Conceptual, not algebraic |

### SymPy verification templates for common econometric proof patterns

**Template 1: Consistency proof — ULLN step**

```python
import sympy as sp
from sympy import symbols, Function, limit, oo, Abs, simplify

# Verify: the objective function Q_n(theta) converges uniformly to Q(theta)
n = symbols('n', positive=True, integer=True)
theta = symbols('theta')

# Define the criterion functions symbolically
Q_n = Function('Q_n')
Q = Function('Q')

# Verify the triangle inequality decomposition:
# |theta_hat - theta_0| <= |Q_n(theta_hat) - Q(theta_hat)| + |Q(theta_hat) - Q(theta_0)|
# This is a structural check — SymPy verifies the inequality holds
a, b, c = symbols('a b c', real=True, nonneg=True)
# Triangle inequality: |a + b| <= |a| + |b|
# Triangle inequality: |a + b| <= |a| + |b|
# SymPy cannot prove general inequalities symbolically, but we verify the
# decomposition structure is correctly applied in the proof
tri_diff = sp.simplify(Abs(a + b) - Abs(a) - Abs(b))
print(f"Triangle inequality residual (symbolic): {tri_diff}")
print("Triangle inequality structure: VERIFIED (decomposition correctly applied)")
```

**Template 2: Score function — information matrix equality**

```python
import sympy as sp

theta = sp.Symbol('theta')
x = sp.Symbol('x')

# For exponential family: verify E[score] = 0
# Log-likelihood: l(theta; x) = theta*x - b(theta) + c(x)
b = sp.Function('b')
l = theta * x - b(theta)
score = sp.diff(l, theta)  # x - b'(theta)
# E[score] = E[x] - b'(theta) = b'(theta) - b'(theta) = 0 (by exponential family property)
print(f"Score function: dl/dtheta = {score}")

# Information matrix: -E[d^2l/dtheta^2] = Var(score)
hessian = sp.diff(l, theta, 2)  # -b''(theta)
print(f"Hessian: d^2l/dtheta^2 = {hessian}")
print(f"Fisher information: I(theta) = {-hessian} = b''(theta)")
print("Information matrix equality structure: VERIFIED")
```

**Template 3: Delta method verification**

```python
import sympy as sp

theta, theta_0, sigma2 = sp.symbols('theta theta_0 sigma2', real=True)
n = sp.Symbol('n', positive=True)

# Delta method: if sqrt(n)(theta_hat - theta_0) -> N(0, sigma^2)
# then sqrt(n)(g(theta_hat) - g(theta_0)) -> N(0, g'(theta_0)^2 * sigma^2)
g = sp.Function('g')

# Verify the Taylor expansion step
g_taylor = g(theta_0) + g(theta).diff(theta).subs(theta, theta_0) * (theta - theta_0)
print(f"First-order Taylor: g(theta) ≈ {g_taylor}")

# Variance transformation
var_original = sigma2
var_transformed = g(theta).diff(theta).subs(theta, theta_0)**2 * sigma2
print(f"Variance after delta method: {var_transformed}")
print("Delta method structure: VERIFIED")
```

**Template 4: GMM moment condition verification**

```python
import sympy as sp

theta = sp.MatrixSymbol('theta', 3, 1)  # parameter vector
g = sp.MatrixSymbol('g', 5, 1)          # moment function (5 moments, 3 params)
W = sp.MatrixSymbol('W', 5, 5)          # weight matrix

# GMM objective: Q(theta) = g(theta)' W g(theta)
Q = g.T * W * g
print(f"GMM objective dimensions: {Q.shape}")  # Should be (1,1)

# FOC: dQ/dtheta = 0 => G' W g = 0 where G = dg/dtheta
G = sp.MatrixSymbol('G', 5, 3)  # Jacobian
foc = G.T * W * g
print(f"FOC dimensions: {foc.shape}")  # Should be (3,1) — one equation per parameter

# Asymptotic variance: (G'WG)^{-1} G'W Omega W G (G'WG)^{-1}
Omega = sp.MatrixSymbol('Omega', 5, 5)
bread = (G.T * W * G)  # 3x3
meat = G.T * W * Omega * W * G  # 3x3
V_gmm = bread.I * meat * bread.I
print(f"Sandwich variance dimensions: {V_gmm.shape}")  # Should be (3,3)

# Efficient GMM: W = Omega^{-1} => V = (G' Omega^{-1} G)^{-1}
print("GMM structure: VERIFIED")
```

### Verification workflow per proof

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Claude       │     │ SymPy        │     │ Codex        │
│ writes proof │────▶│ verifies     │────▶│ reviews      │
│              │     │ algebra      │     │ logic        │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Reconciliation │
                    │  (Claude)       │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  Final proof   │
                    │  + log entry   │
                    └────────────────┘
```

---

## Section 8: Style-Matching System

### Style profile schema

The report must include this JSON schema for `workspace/style_profile.json`:

```json
{
  "source_papers": ["paper1.pdf", "paper2.pdf"],
  "sentence_metrics": {
    "mean_length_words": 22.5,
    "std_length_words": 8.3,
    "min_length_words": 4,
    "max_length_words": 52,
    "distribution": "right-skewed"
  },
  "paragraph_metrics": {
    "mean_length_sentences": 5.2,
    "std_length_sentences": 2.1,
    "mean_length_words": 117,
    "typical_structure": "varied"
  },
  "voice": {
    "active_passive_ratio": 0.65,
    "first_person_usage": "we (plural, even single-author)",
    "preferred_constructions": [
      "We show that...",
      "It follows from Assumption X that...",
      "The key insight is that...",
      "To see this, note that..."
    ],
    "avoided_constructions": [
      "It is important to note that...",
      "It is worth noting that...",
      "In this section, we will..."
    ]
  },
  "citation_style": {
    "narrative_ratio": 0.4,
    "parenthetical_ratio": 0.6,
    "typical_patterns": [
      "Following Hansen (2022), we...",
      "This result extends the framework of Newey and McFadden (1994).",
      "See, e.g., Wooldridge (2010, Ch. 5) for details."
    ]
  },
  "mathematical_conventions": {
    "theorem_prefix": "Theorem",
    "proof_ending": "\\qed",
    "assumption_style": "Assumption A1, A2, ...",
    "equation_numbering": "by section (e.g., (3.1), (3.2))",
    "display_vs_inline_threshold": "equations with more than 2 terms displayed"
  },
  "distinctive_phrases": [
    "under standard regularity conditions",
    "straightforward algebra shows",
    "the remainder term is o_p(1)",
    "by a standard argument"
  ],
  "transition_patterns": [
    "We now turn to...",
    "The next result shows...",
    "Combining the above results...",
    "Section N below provides..."
  ],
  "formatting_preferences": {
    "oxford_comma": true,
    "spellout_numbers_below": 10,
    "abbreviations": ["i.e.,", "e.g.,", "cf.", "w.r.t."]
  }
}
```

### Anti-AI-detection checklist

The report must include this checklist, applied during Phase 7B style matching.
These markers are adapted from the THESIS_EVALUATOR.md Module 5 detection criteria:

**Structural markers (flag and fix):**
- [ ] Formulaic paragraph structure (topic sentence → elaboration → concluding
      sentence in every paragraph) — vary the pattern
- [ ] Uniform paragraph length throughout a section — introduce natural variation
- [ ] Every paragraph starts with a transitional phrase — some should start
      abruptly, as humans do
- [ ] Systematic "on the one hand / on the other hand" constructions — replace
      with more natural contrast patterns
- [ ] Each section has exactly the same structure (intro paragraph, N body
      paragraphs, conclusion paragraph) — break the mold

**Lexical markers (flag and fix):**
- [ ] Excessive hedging: "it is important to note that", "it is worth noting",
      "it should be noted that" — delete or replace with direct statement
- [ ] Repetitive transition phrases: "Furthermore," "Moreover," "Additionally,"
      appearing in sequence — vary or remove
- [ ] Suspiciously smooth prose in technical sections (real math writing is
      terse, sometimes awkward)
- [ ] Perfect grammar and spelling throughout — while good writing is expected,
      uniformly flawless text across 50+ pages is a marker
- [ ] Generic academic filler: "This paper contributes to the growing literature
      on..." — replace with specific claims

**Burstiness check (measure and adjust):**
- Compute sentence length variance per section
- Compare against style_profile.json sentence length distribution
- If variance is lower than the user's natural writing: inject more variation
- Human academic writing has high burstiness: short punchy sentences mixed with
  long complex ones. LLM text tends toward medium-length uniformity.

**Voice consistency check:**
- Compare each section's voice against the style profile
- Flag sections where the author's distinctive phrases disappear
- Flag sections where the voice shifts noticeably (e.g., introduction sounds
  like the author but methodology sounds like ChatGPT)

---

## Section 9: Implementation Report Specification

The final output `IMPLEMENTATION_REPORT.md` must contain all of the following
sections. This is the specification — the architect must fill in all details
based on the analysis and research conducted.

### 9.1 Architecture Diagram (ASCII)

```
┌──────────────────────────────────────────────────────────────────┐
│                    RESEARCH PAPER WORKFLOW                        │
│                                                                  │
│  ┌─────────┐   ┌───────────┐   ┌──────────┐   ┌─────────────┐  │
│  │ Phase 0  │──▶│  Phase 1   │──▶│ Phase 2  │──▶│   Phase 3   │  │
│  │Bootstrap │   │ Doc Process│   │ Ingest   │   │  Planning   │  │
│  └─────────┘   └───────────┘   └──────────┘   └──────┬──────┘  │
│                                                       │          │
│                              ┌────────────────────────┘          │
│                              ▼                                   │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐                    │
│  │ Phase 5  │◀──│  Phase 4   │   │  Codex   │◀─── adversarial   │
│  │Contribut.│   │ Critique   │◀──│  CLI     │     verification  │
│  └────┬─────┘   └───────────┘   └──────────┘                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐   ┌───────────────────────────────────────────┐   │
│  │ Phase 6  │──▶│              Phase 7                       │   │
│  │Final Plan│   │  ┌──────┐  ┌──────┐  ┌────────────────┐   │   │
│  └──────────┘   │  │ 7A   │  │ 7B   │  │ 7C Integration │   │   │
│                 │  │ Math  │  │Prose │  │ & Revision     │   │   │
│                 │  │+SymPy │  │+Style│  │                │   │   │
│                 │  │+Codex │  │Match │  │                │   │   │
│                 │  └──────┘  └──────┘  └────────────────┘   │   │
│                 └───────────────────────────┬─────────────────┘   │
│                                             │                    │
│       ┌─────────────────────────────────────┘                    │
│       ▼                                                          │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐                    │
│  │ Phase 8  │──▶│  Phase 9   │──▶│ Phase 10 │                    │
│  │Adversar. │   │  LaTeX     │   │ Logging  │                    │
│  │Verificat.│   │  Output    │   │ Summary  │                    │
│  └──────────┘   └───────────┘   └──────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 File Manifest

The report must list every file the workflow produces, with description and
purpose. Organized by directory:

```
workspace/                          # All intermediate artifacts
├── session_config.json             # System info + merged config
├── raw_inventory.json              # Inventory of raw/ contents
├── context_analysis.json           # Research context profile
├── paper_profile.json              # Draft paper analysis
├── reference_map.json              # Reference paper summaries
├── style_profile.json              # Writing style profile
├── quality_bar.json                # Target journal standards
├── research_findings.json          # Web research results
├── research_plan.md                # Initial research plan
├── plan_review.md                  # Codex critique of plan
├── critique_log.json               # All critique iterations
├── contribution_assessment.json    # Novelty evaluation
├── final_plan.md                   # Merged final plan
├── extraction_quality.json         # PDF extraction quality scores
├── verification_report.json        # Final verification results
├── math/                           # Theorem/proof .tex files
│   ├── thm_*.tex                   # Individual theorems
│   ├── proof_*.tex                 # Individual proofs
│   ├── verify_*.py                 # SymPy verification scripts
│   ├── review_*.md                 # Codex proof reviews
│   └── verification_log.json       # Math verification results
├── empirical_avenues.md            # Proposed applications & data analyses (Phase 7D)
├── simulation_design.md            # Detailed Monte Carlo design (Phase 7D)
├── empirical_review.md             # Codex review of proposals (Phase 7D)
├── sections/                       # Section .tex files
│   └── NN_section_name.tex
├── paper.tex                       # Assembled paper
└── .venv/                          # Python virtual environment

cleaned/                            # Preprocessed documents
├── reference/
├── style/
├── objective/
└── draft/

output/                             # Final deliverables
├── paper.tex
├── references.bib
├── figures/
├── tables/
└── paper.pdf

logs/                               # Execution logs
├── summary.md
├── phase_*.json
└── token_usage.json

scripts/                            # Reusable workflow scripts
├── bootstrap.sh
├── extract_pdfs.py
├── regex_latex_fix.py
├── verify_equations.py
├── build_style_profile.py
├── verify_proof.py
├── invoke_codex.py
└── compile_latex.sh
```

### 9.3 Dependency List

The report must include a complete `requirements.txt` with pinned versions
and justification for each dependency.

### 9.4 Phase-by-Phase Implementation Guide

For each of the 10 phases, the report must provide:
- Purpose (1-2 sentences)
- Inputs (file paths)
- Outputs (file paths)
- Implementation approach (detailed, with code snippets)
- Error handling (what can go wrong, how to recover)
- Time budget
- Verification criteria (how to know the phase succeeded)

### 9.5 Codex Integration Templates

The report must include ready-to-use Codex prompt templates for:
- Plan critique (Phase 4)
- Proof review (Phase 7A) — one template per proof type
- Full mathematical audit (Phase 8)
- Internal consistency check (Phase 8)

Each template must be a complete, copy-pasteable command.

### 9.6 SymPy Verification Templates

The report must include SymPy templates for common econometric proof patterns:
- Consistency (ULLN-based)
- Asymptotic normality (CLT-based)
- Delta method
- GMM estimation
- Information matrix equality
- Cramér-Rao lower bound
- Wald, LM, and LR test statistics

Each template must be syntactically correct Python that runs without error
(on appropriate symbolic inputs).

### 9.7 Style Profile JSON Schema

Full schema as specified in Section 8, adapted to the specific user's style
(based on analysis of style/ papers).

### 9.8 LaTeX Paper Template

The report must include a recommended LaTeX template structure (adapted from
`raw/template.tex` if available), with:
- Preamble with all necessary packages
- Theorem/proof environments
- Standard econometrics paper sections
- BibTeX setup
- Cross-referencing conventions

### 9.9 config.yaml Schema

Full schema with all options, types, defaults, and descriptions.

### 9.10 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PDF extraction garbles equations | High | High | Triple extraction chain + quality scoring |
| SymPy cannot verify proof step | Medium | Medium | Document limitation, rely on Codex + human |
| Codex CLI unavailable | Medium | Medium | Claude self-critique fallback |
| LaTeX compilation fails | Low | High | 4-level fallback chain |
| Style matching converges to generic | Medium | High | Explicit anti-AI checklist + variance checks |
| Proof has logical error | Low | Critical | Triple verification + explicit assumption tracking |
| Token budget exceeded | Medium | Medium | Phase-level budgets + early stopping |
| Reference paper not accessible | High | Low | Web search fallback + document gap |

### 9.11 Estimated Token Costs

The report must estimate input/output tokens per phase, based on:
- Document sizes (from raw/ inventory)
- Number of theorems and proofs
- Number of sections
- Number of Codex invocations
- Style-matching iterations

Provide cost estimates at both Claude Opus and Sonnet pricing.

### 9.12 GitHub Repo Structure

The report must specify the complete repo structure for the reusable workflow:

```
research-paper-workflow/
├── README.md                       # Setup and usage instructions
├── LICENSE                         # MIT
├── RESEARCH_WORKFLOW_ARCHITECT.md  # This meta-prompt
├── requirements.txt                # Python dependencies
├── config.example.yaml             # Example config with all options
├── scripts/
│   ├── bootstrap.sh                # Environment setup
│   ├── extract_pdfs.py             # PDF → Markdown pipeline
│   ├── regex_latex_fix.py          # LaTeX equation cleanup
│   ├── verify_equations.py         # Extraction quality scoring
│   ├── build_style_profile.py      # Style analysis from user's papers
│   ├── verify_proof.py             # SymPy proof verification
│   ├── invoke_codex.py             # Codex CLI wrapper with retry
│   ├── compile_latex.sh            # LaTeX compilation with fallbacks
│   └── build_report.py             # Implementation report generator
├── templates/
│   ├── paper_econometrica.tex      # Econometrica template
│   ├── paper_aer.tex               # AER template
│   ├── paper_generic.tex           # Generic economics template
│   └── style_profile_schema.json   # Style profile JSON schema
├── prompts/
│   ├── plan_critique.md            # Codex plan critique prompt
│   ├── proof_review.md             # Codex proof review prompt
│   ├── math_audit.md               # Codex full math audit prompt
│   └── consistency_check.md        # Codex consistency check prompt
├── examples/
│   └── example_config.yaml         # Full config with comments
└── .github/
    └── workflows/
        └── test.yml                # CI: lint + template compilation check
```

---

## Section 10: Startup Sequence

When this prompt starts executing, follow this exact sequence:

### Step 1: Environment detection (2 min max)

```bash
# Create directories
mkdir -p workspace cleaned logs output scripts

# System info
echo "=== System Info ==="
python3 --version
uname -a
df -h . | tail -1
sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo "unknown"
sysctl -n hw.memsize 2>/dev/null || free -b 2>/dev/null | grep Mem | awk '{print $2}' || echo "unknown"

# Tool availability
which codex 2>/dev/null && echo "Codex: available" || echo "Codex: NOT available"
which tectonic 2>/dev/null && echo "Tectonic: available" || echo "Tectonic: NOT available"
which latexmk 2>/dev/null && echo "Latexmk: available" || echo "Latexmk: NOT available"
python3 -c "import sympy; print(f'SymPy: {sympy.__version__}')" 2>/dev/null || echo "SymPy: NOT installed"
python3 -c "import marker; print('Marker: available')" 2>/dev/null || echo "Marker: NOT available"
```

### Step 2: Input inventory (2 min max)

```bash
# Count and list files per category
echo "=== Raw Input Inventory ==="
for dir in raw/reference raw/style raw/objective raw/draft; do
  if [ -d "$dir" ]; then
    count=$(find "$dir" -type f | wc -l)
    echo "$dir: $count files"
    find "$dir" -type f -exec ls -lh {} \;
  else
    echo "$dir: MISSING"
  fi
done

# Check for template and config
[ -f "raw/template.tex" ] && echo "Template: found" || echo "Template: MISSING"
[ -f "config.yaml" ] && echo "Config: found" || echo "Config: using defaults"

# Check for previous run artifacts
[ -d "cleaned" ] && [ "$(ls -A cleaned 2>/dev/null)" ] && echo "Cleaned: found (previous run)" || echo "Cleaned: empty (will process)"
```

### Step 3: Checkpoint detection and resume logic

Check for artifacts from a previous (possibly interrupted) run. The workflow
saves checkpoints after each major phase. On restart, skip completed phases.

```bash
# Check for checkpoint file
if [ -f "workspace/checkpoint.json" ]; then
  echo "=== PREVIOUS RUN DETECTED ==="
  cat workspace/checkpoint.json
  echo ""
  echo "Will resume from last completed phase."
fi
```

The checkpoint file tracks which phases completed successfully:
```json
// workspace/checkpoint.json
{
  "run_id": "2025-02-10T14:30:00Z",
  "phases_completed": {
    "phase_0_bootstrap": {"status": "done", "timestamp": "...", "duration_min": 3},
    "phase_1_document_processing": {"status": "done", "timestamp": "...", "duration_min": 12},
    "phase_2_ingestion": {"status": "done", "timestamp": "...", "duration_min": 25},
    "phase_3_planning": {"status": "in_progress", "timestamp": "...", "started": "..."}
  },
  "last_completed_phase": "phase_2_ingestion",
  "resume_from": "phase_3_planning"
}
```

**Resume protocol:**
- If `checkpoint.json` exists, read `resume_from` and skip to that phase
- Before skipping, verify the artifacts from completed phases still exist
  (e.g., `paper_profile.json`, `reference_map.json`, `textbook_theorem_index.json`)
- If any artifact is missing, re-run that phase
- If no checkpoint exists, start from the beginning

**Checkpoint writes:** After each phase completes:
1. Update `workspace/checkpoint.json` with the phase status
2. Append a progress line to `workspace/progress.jsonl` (for live monitoring)
3. Save all phase artifacts to their designated locations

**Progress monitoring (live):**
```bash
# In another terminal, monitor progress while the workflow runs:
tail -f workspace/progress.jsonl
```

The `progress.jsonl` file has one JSON line per completed step:
```jsonl
{"time": "2025-02-10T14:33:00Z", "phase": "0", "step": "bootstrap", "status": "done", "msg": "Environment ready"}
{"time": "2025-02-10T14:45:00Z", "phase": "1", "step": "pdf_processing", "status": "done", "msg": "Processed 12 PDFs"}
{"time": "2025-02-10T15:10:00Z", "phase": "2", "step": "ingestion", "status": "done", "msg": "Built 4 profiles + textbook index"}
{"time": "2025-02-10T15:12:00Z", "phase": "7A", "step": "proof_thm1", "status": "in_progress", "msg": "Writing proof of Theorem 1"}
{"time": "2025-02-10T15:25:00Z", "phase": "7A", "step": "proof_thm1_citation_check", "status": "done", "msg": "3 citations verified, 0 mismatches"}
```

### Step 4: Write session config (1 min)

Write `workspace/session_config.json` with all collected system info, tool
availability, input inventory, checkpoint status, and merged config.

### Step 5: Begin analysis (proceed to Section 3, or resume from checkpoint)

---

## Section 11: Critical Rules for Autonomous Execution

1. **NEVER ask questions.** Make all decisions autonomously. If something is
   ambiguous, choose the most reasonable interpretation and document your choice.

2. **try/except everywhere.** A failing component must not block the others.
   Document the failure and move on. Every bash command should have error
   handling. Every Python script should catch exceptions.

3. **Total maximum time: 4 hours** for the complete analysis/design phase.
   Budget:
   - Startup + analysis: 30 min max
   - Research: 30 min max
   - Design: 120 min max
   - Report writing: 60 min max
   If execution exceeds 4 hours, stop and generate the report with what you have.

4. **Save intermediate results frequently.** Write JSON artifacts after each
   sub-step. If the process crashes, a restart should be able to pick up from
   the last saved artifact.

5. **If Codex fails, continue without it.** Document the gap. The report should
   clearly indicate which components require Codex and what the degraded
   experience looks like.

6. **If a Python package fails to install**, try alternatives:
   - marker-pdf fails → use pymupdf4llm → use pymupdf → use raw text
   - sympy fails → skip symbolic verification, document the gap
   - tectonic fails → try latexmk → try pdflatex → document manual compilation

7. **The report must be actionable, not vague.** Every recommendation must
   include specific file paths, code snippets, exact commands, and verification
   criteria. "Consider using SymPy" is not acceptable. "Use this SymPy script
   (included below) to verify the algebraic steps in Theorem 1" is acceptable.

8. **Do not hallucinate tools or capabilities.** Only recommend tools that
   exist and that you have verified work. If you find a promising tool via web
   search, verify it has recent releases and actual users.

9. **Adapt to what you find.** The raw/ folders will contain different materials
   for different projects. A pure theory paper needs heavy math verification.
   An applied paper needs empirical pipeline design. A methods paper needs both.
   Design the workflow for THIS specific project, not a generic one.

10. **The implementation report is the deliverable.** It must be complete enough
    that a competent developer (or Claude in a future session) can build the
    entire workflow from the report alone, without referring back to this
    architect prompt.

11. **Web search is essential.** Do not skip the research phase. Recent advances
    in AI-assisted writing, new tools, and new techniques should inform the design.
    Search broadly and synthesize what you find.

12. **Style matching is critical.** The user wants the paper to sound like they
    wrote it, not like AI wrote it. The style profile must be detailed and the
    matching loop must be rigorous. This is not optional.

13. **Mathematical rigor is non-negotiable.** Every proof must be verified by
    at least three independent methods: textbook citation ground-truth check,
    SymPy algebraic verification, and Codex adversarial review. Single-method
    verification is insufficient for publication-quality proofs.

14. **Never trust LLM memory of a theorem.** When citing a textbook result in
    a proof, ALWAYS re-read the actual source PDF at the cited page. Verify:
    (a) the theorem exists at the stated location, (b) the statement matches
    what is claimed, (c) ALL conditions are satisfied. LLMs confidently
    hallucinate theorem numbers, misstate conditions, and misapply results.
    A referee with the book on their desk will catch this instantly.

15. **Log everything.** At the `standard` log level, every phase should produce
    a structured JSON log. The summary log must give a clear picture of what was
    done, what succeeded, and what needs attention.

16. **The config.yaml is optional.** If absent, infer all settings from the raw/
    contents. The system must be fully autonomous even with zero configuration.

---

## Start

Begin NOW. Execute the startup sequence (Section 10), then proceed through
Sections 3 and 4 (analysis and research), then design the full workflow
(Section 5), and finally produce `IMPLEMENTATION_REPORT.md` (Section 9).

Do not stop until `IMPLEMENTATION_REPORT.md` is written and complete.

Good luck.
