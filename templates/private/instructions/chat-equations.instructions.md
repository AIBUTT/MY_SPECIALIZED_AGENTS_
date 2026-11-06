---
applyTo: "**"
description: "Human-readable equations in every role's chat replies."
---
# Equations in chat

- All roles, including the Coordinator, write chat equations in plain ASCII and define their terms. Example: `delta = abs(d_candidate) - abs(d_reference)`.
- Do not assume that a chat client renders mathematics. Do not use raw LaTeX commands or inline/display LaTeX delimiters in chat unless the user explicitly requests LaTeX source.
- Preserve LaTeX in Markdown report sources and rendered reports. This chat rule does not change scientific notation in source artifacts.
- Offer rendered offline reports for readers who do not use Markdown tools.
