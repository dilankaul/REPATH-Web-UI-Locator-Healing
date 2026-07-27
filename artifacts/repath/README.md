# REPATH calibration inputs

This directory contains the latest supplied calibration inputs:

- `repath_query_manifest.csv`: one row per framework query, including its site and split.
- `development_oof_candidate_scores.csv`: pooled four-fold development out-of-fold candidate scores.
- `test_candidate_scores.csv`: held-out test candidate scores.

The calibration command uses the development OOF scores to select tau and applies that frozen threshold to the held-out test scores. Each retrievable query must have exactly one positive candidate (`label == 1`).

Replace all three files together when rerunning the feature-generation and training notebooks.
