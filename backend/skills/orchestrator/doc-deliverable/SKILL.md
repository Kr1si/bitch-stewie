---
name: doc-deliverable
description: Produce documentation deliverables (Markdown in repo, docx/pdf for stakeholders). Use when the user asks for docs, ADR write-ups, or formal documents.
---

# Documentation deliverables

1. Ground the draft: `list_decisions` for the project, `search_knowledge` for
   related standards/notes, `list_preferences` for style conventions.
2. Draft in clean Markdown. Structure for architecture docs: Context,
   Decision/Design, Consequences/Risks, References. Cite knowledge-base
   sources by their `source` field.
3. Destination:
   - living docs → Markdown committed to the repo (delegate a coding task if
     it must land in git with review),
   - stakeholder deliverables → `export_document` (.docx/.pdf) into the
     project's docs/ folder.
4. Show the user the draft BEFORE exporting; export is the last step.
