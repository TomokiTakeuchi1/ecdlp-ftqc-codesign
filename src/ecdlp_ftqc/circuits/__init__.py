"""Architecture-independent circuit frontends and adapters."""

from ecdlp_ftqc.circuits.gidney_adapter import (
    GIDNEY_SOURCE_REPOSITORY,
    PINNED_GIDNEY_SOURCE_COMMIT,
    GidneyAdapterError,
    adapt_gidney_oracle,
    generate_gidney_dag,
    load_gidney_oracle_dag,
)

__all__ = [
    "GIDNEY_SOURCE_REPOSITORY",
    "PINNED_GIDNEY_SOURCE_COMMIT",
    "GidneyAdapterError",
    "adapt_gidney_oracle",
    "generate_gidney_dag",
    "load_gidney_oracle_dag",
]
