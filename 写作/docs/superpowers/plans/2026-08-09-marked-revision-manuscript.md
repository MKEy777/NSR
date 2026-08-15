# Marked Revision Manuscript Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained, compilable Marked Revised Manuscript whose effective content is exactly `NSR_Author/main.tex` and whose substantive changes from `docs/original_main.tex` are visibly marked.

**Architecture:** Use `NSR_Author/` as the immutable content source and copy it into `marked_revision/`. Compare the two rendered-LaTeX sources by logical units, then apply syntax-safe marking only in the copied `main.tex`; preserve labels, references, source paths, assets, bibliography data, and document ordering. Validate with the original LaTeX toolchain and a marker-stripping equivalence check.

**Tech Stack:** LaTeX (`pdflatex`/BibTeX or the detected project build command), `xcolor`, `ulem`, PowerShell inspection utilities, and `latexdiff` only as a diagnostic aid.

## Global Constraints

- Revised source is the sole final-content authority; do not rewrite, correct, reorder, or normalize its prose or data.
- Do not modify `docs/original_main.tex` or `NSR_Author/`.
- Keep revised directory structure and all non-TeX assets unchanged in `marked_revision/`.
- Do not alter any `\\label{}` key, citation key, cross-reference key, figure path, figure order, table structure, or bibliography data.
- Prioritize compilability, then exact revised effective content, then visible additions/modifications, then visible deletions.

---

### Task 1: Establish the comparison inventory

**Files:**
- Read: `docs/original_main.tex`
- Read: `NSR_Author/main.tex`
- Read: `NSR_Author/nsr.cls`, `NSR_Author/nsr_sample.bib`

**Interfaces:**
- Consumes: Original and revised LaTeX sources.
- Produces: A section-level inventory of substantive prose, mathematical, tabular, caption, and citation differences.

- [ ] **Step 1: Inspect document structure and source dependencies**

Run: `rg -n '^\\(documentclass|usepackage|section|subsection|begin|end|bibliography|input|include)' docs/original_main.tex NSR_Author/main.tex`

Expected: Both sources are identified as single-file manuscripts with their section structure and revised dependencies known.

- [ ] **Step 2: Generate a token-aware diagnostic diff**

Run: `latexdiff --type=UNDERLINE --flatten docs/original_main.tex NSR_Author/main.tex > marked_revision-diagnostic.tex`

Expected: Diagnostic output is used only to locate candidate changes; no diagnostic source is submitted.

- [ ] **Step 3: Manually classify candidate changes by logical rendered unit**

Check prose, equations, captions, cells, citations, and section titles against the sources.

Expected: Formatting-only differences are excluded and unsafe deletion candidates are listed.

### Task 2: Build the marked manuscript safely

**Files:**
- Create: `marked_revision/` (copy of `NSR_Author/`)
- Modify: `marked_revision/main.tex`
- Create: `marked_revision/change_summary.md`

**Interfaces:**
- Consumes: The classified difference inventory from Task 1.
- Produces: The compilable marked LaTeX manuscript and a human-readable audit summary.

- [ ] **Step 1: Copy revised project without altering the source project**

Run: `Copy-Item -Recurse NSR_Author marked_revision`

Expected: `marked_revision/main.tex` initially equals `NSR_Author/main.tex` byte-for-byte.

- [ ] **Step 2: Add marker macros to the copied preamble**

Insert exactly syntax-safe `xcolor`/`ulem`-based macros for additions, deletions, and replacements. Keep the existing table-color package loading compatible.

Expected: Blue additions and red strike-through deletions/replacements are available without changing source content outside annotations.

- [ ] **Step 3: Apply logical-unit markings**

Use `\\added{}` for inserted text, `\\changed{old}{new}` for safe prose replacements, and blue-only revised content for equations, references, or table syntax where deletion markup would be unsafe.

Expected: Text, captions, numeric cells, and citations are marked minimally without wrapping structural LaTeX tokens in unsafe macros.

- [ ] **Step 4: Write the change summary**

Create `marked_revision/change_summary.md` with concise section-level changes and a record of blue-only safety fallbacks.

Expected: Summary supports review but does not replace manuscript annotations.

### Task 3: Verify exactness and buildability

**Files:**
- Read: `marked_revision/main.tex`
- Generate: `marked_revision/main.pdf` and compiler auxiliary files

**Interfaces:**
- Consumes: Marked manuscript from Task 2.
- Produces: Successful PDF and verification evidence.

- [ ] **Step 1: Run LaTeX compilation from the marked project directory**

Run the detected original-compatible command (`latexmk -pdf main.tex`, or `pdflatex`/`bibtex` passes).

Expected: A `main.pdf` is generated with no LaTeX Error or undefined control sequence.

- [ ] **Step 2: Inspect compiler log for structural failures**

Run: `rg -n 'LaTeX Error|Undefined control sequence|Emergency stop|Undefined references|Undefined citations' marked_revision/main.log`

Expected: No fatal issue remains; any first-pass bibliography warnings are cleared by reruns.

- [ ] **Step 3: Perform reverse content validation**

Derive a temporary copy by stripping marker wrappers and deletion-only branches, then compare its logical LaTeX content with `NSR_Author/main.tex` while excluding the intentional preamble macro additions.

Expected: The effective revised content and all labels, references, and structural environments match.

- [ ] **Step 4: Visually inspect the PDF**

Render or open representative pages containing equations, large tables, figures, and the bibliography.

Expected: Markup is visible, tables and formulas are readable, and no page suffers from syntax-induced layout failure.
