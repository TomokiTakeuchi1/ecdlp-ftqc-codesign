"""Architecture-independent research analyses."""

from .qcla_clifford_strategy import (
    CLIFFORD_STRATEGY_SCHEMA,
    CLIFFORD_STRATEGY_SCHEMA_VERSION,
    ExecutionOption,
    GateKind,
    HandlingMode,
    SourceLayerCliffordDemand,
    StrategyEffect,
    VariantCliffordDemand,
    analyze_qcla_clifford_demand,
    build_execution_options,
    build_strategy_matrix,
    execution_option_to_data,
    strategy_effect_to_data,
    variant_clifford_demand_to_data,
)

__all__ = [
    "CLIFFORD_STRATEGY_SCHEMA",
    "CLIFFORD_STRATEGY_SCHEMA_VERSION",
    "ExecutionOption",
    "GateKind",
    "HandlingMode",
    "SourceLayerCliffordDemand",
    "StrategyEffect",
    "VariantCliffordDemand",
    "analyze_qcla_clifford_demand",
    "build_execution_options",
    "build_strategy_matrix",
    "execution_option_to_data",
    "strategy_effect_to_data",
    "variant_clifford_demand_to_data",
]
