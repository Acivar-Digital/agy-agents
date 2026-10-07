"""
Modular import shim for the Deep Research engine.
Allows standard Python imports:
    from deep_research import execute_research, run_deep_research
"""
import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parent / "deep-research" / "deep-research.py"

_spec = importlib.util.spec_from_file_location("_deep_research_impl", _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

execute_research = _mod.execute_research
get_provider_config = _mod.get_provider_config
download_and_extract_sandbox = _mod.download_and_extract_sandbox
run_deep_research = _mod.run_deep_research

# Pydantic V2 models & type aliases
ProviderConfig = _mod.ProviderConfig
InteractionRequest = _mod.InteractionRequest
InteractionStep = _mod.InteractionStep
InteractionResponse = _mod.InteractionResponse
ResearchExecutionRequest = _mod.ResearchExecutionRequest
ResearchExecutionResult = _mod.ResearchExecutionResult
ProviderChoice = _mod.ProviderChoice
ActiveProvider = _mod.ActiveProvider

__all__ = [
    "execute_research",
    "get_provider_config",
    "download_and_extract_sandbox",
    "run_deep_research",
    "ProviderConfig",
    "InteractionRequest",
    "InteractionStep",
    "InteractionResponse",
    "ResearchExecutionRequest",
    "ResearchExecutionResult",
    "ProviderChoice",
    "ActiveProvider",
]
