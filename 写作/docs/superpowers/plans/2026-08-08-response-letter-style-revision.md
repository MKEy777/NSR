# Reviewer Response Style Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite all 42 response passages so that each directly develops the scientific answer with less repetitive framing while preserving every verified fact and submission artifact.

**Architecture:** Edit only response prose and location-introduction sentences in one LaTeX source. Treat each reviewer as an independent review batch, then run document-wide invariance checks against the reviewer comments, manuscript excerpts, tables, figures, references, and current manuscript sources.

**Tech Stack:** LaTeX, PowerShell text audits, `latexmk`.

## Global Constraints

- Preserve all 42 reviewer comments verbatim.
- Preserve all numerical values, equations, section names, displayed manuscript excerpts, figures, tables, captions, and bibliography entries.
- Retain `Comment X.X`, `Response to Comment X.X`, and conditional `Reference to Comment X.X` headings.
- Do not modify `main.tex`, `supplement.tex`, or `response_to_reviewers_中文.md`.
- Use section names rather than line numbers.
- Do not perform visual PDF inspection.

---

### Task 1: Rewrite Reviewer 1 Responses

**Files:**
- Modify: `NSR_Author/response_to_reviewers.tex`

- [x] Rewrite Responses 1.1--1.7 using direct assessment, action, evidence, and limitation as appropriate.
- [x] Replace repeated generic location introductions with comment-specific sentences.
- [x] Verify that Reviewer 1 comments, excerpts, figures, tables, captions, numbers, and references are unchanged.

### Task 2: Rewrite Reviewer 2 Responses

**Files:**
- Modify: `NSR_Author/response_to_reviewers.tex`

- [x] Rewrite Responses 2.1--2.6, retaining explicit comparison boundaries and deployment limitations.
- [x] Ensure partial acceptance in Responses 2.3--2.5 is stated transparently.
- [x] Verify that Reviewer 2 comments, excerpts, tables, captions, numbers, and references are unchanged.

### Task 3: Rewrite Reviewer 3 Responses

**Files:**
- Modify: `NSR_Author/response_to_reviewers.tex`

- [x] Rewrite Responses 3.1--3.6 with results-forward openings and concise methodological explanations.
- [x] Keep robustness and variability claims calibrated to their actual evaluation units.
- [x] Verify that Reviewer 3 comments, excerpts, figures, captions, numbers, and references are unchanged.

### Task 4: Rewrite Reviewer 4 Responses

**Files:**
- Modify: `NSR_Author/response_to_reviewers.tex`

- [x] Rewrite Responses 4.1--4.23, shortening simple presentation replies and expanding only mathematical, validation, and limited-acceptance arguments.
- [x] Make Responses 4.10, 4.15, and 4.16 distinguish inherited B1 properties, local derivatives, and unsupported network-level stability claims.
- [x] Make Response 4.5 transparent that the figure retains a graphical operator node while equations use `\odot`.
- [x] Verify that Reviewer 4 comments, excerpts, figures, captions, numbers, and references are unchanged.

### Task 5: Run Invariance and Build Checks

**Files:**
- Verify: `NSR_Author/response_to_reviewers.tex`
- Compare: `NSR_Author/main.tex`
- Compare: `NSR_Author/supplement.tex`

- [x] Count exactly 42 comments and 42 responses and confirm matching IDs.
- [x] Confirm all 45 displayed manuscript excerpts match current manuscript or supplement text after whitespace normalization.
- [x] Confirm all five embedded table bodies and all figure captions are unchanged.
- [x] Confirm `Reference to Comment` appears only for displayed text containing citations.
- [x] Scan for repetitive empty thanks, generic location sentences, forbidden meta-language, and altered numerical tokens.
- [x] Run `latexmk -g -pdf -interaction=nonstopmode -halt-on-error response_to_reviewers.tex` and require exit code 0.
