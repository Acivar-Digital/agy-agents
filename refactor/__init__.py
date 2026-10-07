"""
Modular import package for the autonomous refactoring engine.
Allows standard Python imports:
    from refactor import execute_refactor, main
"""
from refactor.refactor import (
    execute_refactor,
    get_provider_config,
    clean_code_fences,
    extract_output_text,
    refactor_file,
    refactor_with_manifest,
    load_manifest,
    load_manifests,
    main,
)

__all__ = [
    "execute_refactor",
    "get_provider_config",
    "clean_code_fences",
    "extract_output_text",
    "refactor_file",
    "refactor_with_manifest",
    "load_manifest",
    "load_manifests",
    "main",
]
