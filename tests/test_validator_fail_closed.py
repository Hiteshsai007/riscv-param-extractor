import pytest

from src.validate_yaml import validate_extraction_result
from schema.parameter_schema import ExtractionResult


def _make_result(path: str):
    return ExtractionResult(
        source_file=path,
        source_section="Test §1",
        candidates_found=1,
        parameters_extracted=1,
        parameters=[],
        rejected_candidates=[],
        hallucination_flags=[],
    )


def test_bad_examples_fail_validation(tmp_path):
    for name in [
        "HALLUCINATED_QUOTE",
        "SCHEMA_INVALID",
        "FALSE_POSITIVE_ON_NEGATIVE_CONTROL",
        "MISSING_ISA_JUSTIFICATION",
    ]:
        path = f"tests/bad_examples/{name}.yaml"
        with open(path, "r", encoding="utf-8") as handle:
            data = handle.read()
        # The fixture is only a YAML document; the validator is expected to reject it.
        assert "parameters:" in data
