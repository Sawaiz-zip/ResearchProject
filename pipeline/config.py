from enum import Enum
from dataclasses import dataclass, field


class AblationMode(str, Enum):
    BASELINE = "baseline"          # no repair loop
    COMPILER_ONLY = "compiler_only"  # repair on iverilog errors only
    PYVERILOG_ONLY = "pyverilog_only"  # repair on static analysis errors only
    HYBRID = "hybrid"              # both sources trigger repair


@dataclass
class PipelineConfig:
    mode: AblationMode = AblationMode.HYBRID
    max_repair_iter: int = 3
    simulation_timeout_s: int = 30
    num_mutants: int = 5           # for Eval2
    results_dir: str = "results"
    prompts_dir: str = "prompts"
    # Models
    model_cheap: str = "claude-haiku-4-5-20251001"   # classify, scenarios, mutants
    model_strong: str = "claude-sonnet-4-6"          # spec, driver, checker, repair, reasoning
