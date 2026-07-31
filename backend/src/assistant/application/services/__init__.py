"""Application services: the seam between the interface layer and infrastructure.

The interface layer imports ONLY from `assistant.application` (these services)
and `assistant.shared`. These facades delegate to `assistant.infrastructure`,
which the interface never imports directly. This keeps the dependency arrow
pointing inward (interface -> application -> infrastructure) so import-linter
can enforce the boundary.
"""
