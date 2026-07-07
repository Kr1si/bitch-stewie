---
name: diagram-update
description: Keep architecture diagrams in sync with the LikeC4 model. Use when architecture changes or the user asks for diagrams.
---

# Diagram pipeline

The LikeC4 model in the project repo is the SINGLE source of truth; .drawio
files are generated exports, never edited as the primary artifact.

- To CHANGE architecture views: delegate a coding task that edits the
  `.likec4` files (model elements, relations, views), then run
  `update_diagrams` to regenerate `<repo>/diagrams/*.drawio`.
- For a quick throwaway sketch the user will refine by hand, generating a
  drawio file directly is acceptable — but say explicitly that it is NOT part
  of the model and won't survive regeneration.
- After regenerating, tell the user which files changed; they preview/edit in
  the embedded draw.io (web UI) or draw.io desktop.
