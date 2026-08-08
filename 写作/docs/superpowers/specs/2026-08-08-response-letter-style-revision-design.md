# Reviewer Response Style Revision Design

## Objective

Revise `NSR_Author/response_to_reviewers.tex` so that each response reads as a reviewer-specific scientific argument rather than a repeated template, while preserving all verified facts and submission structure.

## Scope

- Rewrite only the prose under the 42 `Response to Comment X.X` headings and the sentences that introduce manuscript locations or displayed revisions.
- Preserve every reviewer comment verbatim.
- Preserve all numerical results, equations, section names, manuscript excerpts, figures, tables, captions, and bibliography entries.
- Retain the established `Comment`, `Response to Comment`, and conditional `Reference to Comment` structure.
- Do not add line numbers or change `main.tex`, `supplement.tex`, or the Chinese Markdown translation.

## Response Pattern

Each response will use the shortest suitable version of this sequence:

1. State the authors' assessment of the concern directly.
2. Explain the relevant scientific or methodological distinction when needed.
3. Identify the action taken and the evidence produced.
4. State the result, limitation, or boundary of the revision.
5. Introduce the exact manuscript location and displayed material with a sentence tailored to that comment.

Simple presentation comments may use one short paragraph. Experimental, mathematical, hardware, and partially accepted requests may use multiple paragraphs.

## Tone

- Cooperative, evidence-led, and non-defensive.
- Thank the reviewer when the comment materially improved the work, but do not begin nearly every response with `We thank` or `We appreciate`.
- For accepted comments, explain why the change improves interpretation or rigor.
- For partially accepted comments, acknowledge the valid premise, define the narrow point not adopted, explain why, and state the compensating revision or claim limitation.
- Avoid empty approval, repetitive intensifiers, promotional wording, and unsupported `We believe` statements.

## Verification

- Confirm 42 comments and 42 matching responses.
- Confirm that all displayed manuscript excerpts still match current `main.tex` or `supplement.tex` exactly.
- Confirm that embedded figures, tables, captions, numerical values, equations, and reference sections are unchanged.
- Confirm that `Reference to Comment` remains only where the displayed material contains a citation.
- Compile with `latexmk -g -pdf -interaction=nonstopmode -halt-on-error`.
- Do not perform visual PDF inspection, as requested by the author.
