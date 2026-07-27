from repath_evaluation.utilities.similarity import levenshtein_distance, normalized_edit_similarity


def test_levenshtein():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("", "abc") == 3


def test_normalized_similarity():
    assert normalized_edit_similarity("abc", "abc") == 1.0
    assert normalized_edit_similarity("", "abc") == 0.0
