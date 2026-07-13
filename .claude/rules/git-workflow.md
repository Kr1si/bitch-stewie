# Git workflow: never push directly to main

All work in this repo goes on a feature branch — never commit or push
directly to `main`. Create a branch named for the task (e.g.
`fix/deploy-nonroot`, `feat/run-start-ui`), commit there, and push the
branch. Do not merge it yourself; the user merges to `main` manually.

This applies to deploys too: `make deploy` / the CI workflow pull from
`origin/main`, so a change only reaches krisiserver after the user has
reviewed and merged the branch.
