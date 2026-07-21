import pytest

from src.eval_harness import (
    _normalize_name,
    _name_similarity,
    compute_precision_recall_relaxed,
)

def test_normalize_name():
    assert _normalize_name("Cache-Block Size") == "cache_block_size"
    assert _normalize_name("cache_block_size") == "cache_block_size"
    assert _normalize_name("  cache  block  size  ") == "cache_block_size"
    assert _normalize_name("CacheBlock Size") == "cacheblock_size" # It doesn't do camelcase splitting by default, just space/hyphen

def test_name_similarity():
    # Exact match
    assert _name_similarity("cache_block_size", "cache_block_size") == 1.0
    
    # Close matches from EXPERIMENTS.md
    sim1 = _name_similarity("cache_block_operation_mechanism", "non_coherent_agent_cbo_mechanism")
    assert sim1 < 0.8 # These are semantically similar but lexically different

    sim2 = _name_similarity("cbo_zero_update_order_and_granularity", "cbo_zero_atomicity_and_granularity")
    assert sim2 >= 0.75

def test_compute_precision_recall_relaxed_exact_match():
    extracted = [
        {"name": "cache_block_size", "type": "numeric_range"}
    ]
    gold = [
        {"name": "cache_block_size", "type": "numeric_range"}
    ]
    
    result = compute_precision_recall_relaxed(extracted, gold)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["true_positives"] == 1

def test_compute_precision_recall_relaxed_similar_name():
    extracted = [
        {"name": "cbo_zero_update_order_and_granularity", "type": "enumerated"}
    ]
    gold = [
        {"name": "cbo_zero_atomicity_and_granularity", "type": "enumerated"}
    ]
    
    result = compute_precision_recall_relaxed(extracted, gold, name_similarity_threshold=0.75)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["true_positives"] == 1
    assert len(result["matches"]) == 1
    assert result["matches"][0]["name_similarity"] >= 0.75

def test_compute_precision_recall_relaxed_wrong_type():
    extracted = [
        {"name": "cache_block_size", "type": "enumerated"} # Wrong type
    ]
    gold = [
        {"name": "cache_block_size", "type": "numeric_range"}
    ]
    
    result = compute_precision_recall_relaxed(extracted, gold)
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["true_positives"] == 0
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 1
