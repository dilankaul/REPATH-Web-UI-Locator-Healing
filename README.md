# REPATH Evaluation Suite

A reproducible evaluation suite for REPATH and five Web-UI element-matching baselines. It combines baseline benchmarking, optional independent end-to-end query timing, REPATH ranking evaluation, exhaustive feature-group ablation reporting, feature-importance reporting, and confidence-margin calibration.

## Capabilities

- Benchmark WATER, VISTA, SFTM, WebEvo, Similo, and REPATH under one fixed Top-1 protocol.
- Select `test` (default), `development`, `all`, one site, or multiple explicit sites.
- Keep the default benchmark fast and omit runtime output unless `--measure-runtime` is enabled.
- Evaluate a user-selected REPATH confidence margin with `--tau`.
- Select a margin automatically using pooled development out-of-fold precision and coverage constraints.
- Display the latest REPATH ranking, calibration, exhaustive ablation, feature-vector, and feature-importance results directly in this README.

## Installation

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest -q
```

```bash
repath-eval --help
```

`repath-benchmark` remains available as a compatibility alias. The old `run` subcommand remains an alias for `benchmark`.

## Repository layout

```text
REPATH-Evaluation-Suite/
├── artifacts/
│   └── repath/              # Bundled manifest and candidate-score calibration inputs
├── configs/
│   └── site_split.yaml
├── data/                    # UITestFix MatchingDataset site folders
├── models/                  # Latest REPATH model, base config, and calibrated config
├── results/
├── src/repath_evaluation/
│   ├── algorithms/
│   ├── calibration/
│   ├── data/
│   └── evaluation/
└── tests/
```

## Dataset setup

This suite uses the dataset released with **UITestFix**:

- Dataset: [Web-UI-Dataset](https://anonymous.4open.science/r/Web-UI-Dataset-9645)
- Paper: Yuanzhang Lin, Guoyao Wen, and Xiang Gao, ["Automated Fixing of Web UI Tests via Iterative Element Matching"](https://doi.org/10.1109/ASE56229.2023.00048), ASE 2023.

Download the dataset and open its `MatchingDataset` folder. Copy the folders **inside** `MatchingDataset` directly into this repository's `data/` directory.

```text
REPATH-Evaluation-Suite/
├── data/
│   ├── amazon-2017-2020/
│   │   ├── old/
│   │   ├── new/
│   │   └── result/
│   ├── beijing-2017-2019/
│   ├── instagram/
│   └── ...
```

Do not create `data/MatchingDataset/...`; each site folder must be an immediate child of `data/`.

```bash
repath-eval inspect
repath-eval doctor
```

A different dataset root is optional:

```bash
repath-eval inspect --data-root /path/to/MatchingDataset
```

## Site groups

The groups are stored in [`configs/site_split.yaml`](configs/site_split.yaml). The latest feature-generation run extracted 782 development and 318 held-out framework queries, for 1,100 total queries.

### Development sites

- `amazon-2017-2020`
- `apple-2018-2020`
- `fandom`
- `Bing`
- `facebook-2020-2022`
- `foodnetwork-2018-2019`
- `google`
- `linkedin-2019-2020`
- `music-2014-2019`
- `paypal`
- `Reddit`
- `twitter-2021-2022`
- `usps-2018-2019`
- `w3school-2016-2019`
- `wikipedia`
- `youtube`

### Held-out test sites

- `book-2016-2019`
- `beijing-2017-2019`
- `instagram`
- `movie-2014-2019`
- `xfinity-2018-2020`
- `yahoo`

The test group is the default:

```bash
repath-eval inspect
repath-eval inspect --sites test
repath-eval inspect --sites development
repath-eval inspect --sites all
repath-eval inspect --sites instagram
repath-eval inspect --sites instagram yahoo xfinity-2018-2020
```

Site and group matching is case-insensitive.

## Benchmarking

```bash
repath-eval benchmark \
  --algorithms water vista sftm webevo similo \
  --repeats 5 \
  --output results/baselines_test
```

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

repath-eval benchmark \
  --algorithms water vista sftm webevo similo repath \
  --sites test \
  --repeats 5 \
  --output results/final_benchmark
```

Single and selected sites remain supported:

```bash
repath-eval benchmark \
  --algorithms water vista sftm webevo similo repath \
  --sites instagram \
  --output results/instagram
```

### Optional end-to-end query runtime

Runtime measurement is disabled by default. Fast execution prepares a page pair and matcher once and omits runtime columns.

```bash
repath-eval benchmark \
  --algorithms water vista sftm webevo similo repath \
  --sites test \
  --repeats 1 \
  --measure-runtime \
  --output results/end_to_end_runtime
```

With `--measure-runtime`, each query independently loads page data, constructs and prepares the matcher, and executes the match inside the timer. REPATH resolves or downloads SBERT before timing; timed executions load it locally. Network download time is excluded, while local model loading and inference are included.

In normal fast mode, each matcher is prepared once per page pair and can reuse algorithm-specific page-level state across queries. WATER reuses the loaded page data, SFTM reuses its tree mapping, Similo reuses candidate and neighbour metadata, VISTA reuses decoded screenshots and scene descriptors, WebEvo reuses ordered candidate metadata, and REPATH reuses prepared feature context. With `--measure-runtime`, a fresh page pair and matcher are created and prepared inside every query timer, so initialization, preprocessing, and cache construction are included in the reported end-to-end runtime for every algorithm.

### Benchmark results

Run the held-out benchmark and enter the resulting values in this table. Top-1 accuracy should come from the normal benchmark output. Mean query execution time should come from a separate run with `--measure-runtime`.

| Algorithm | Top-1 accuracy | Mean end-to-end query time (ms) |
| --------- | -------------: | ------------------------------: |
| WATER     |                |                                 |
| VISTA     |                |                                 |
| SFTM      |                |                                 |
| WebEvo    |                |                                 |
| Similo    |                |                                 |
| REPATH    |                |                                 |

## REPATH confidence-margin calibration

The latest calibration inputs are already included:

```text
artifacts/repath/
├── repath_query_manifest.csv
├── development_oof_candidate_scores.csv
└── test_candidate_scores.csv
```

Automatically select tau using development out-of-fold predictions only:

```bash
repath-eval calibrate \
  --output results/calibration_auto
```

The default selector reproduces the latest notebook protocol: target precision `0.99`, minimum end-to-end coverage `0.80`, and a tau grid from `0.00` to `1.00` in steps of `0.05`. With the bundled artifacts, it selects `tau = 0.40`.

Evaluate that fixed operating point without reselecting it:

```bash
repath-eval calibrate \
  --tau 0.40 \
  --output results/calibration_tau_040
```

The repository also includes `models/config.pkl`, generated from `models/config_base.pkl` using the selected `tau = 0.40`. Regenerate it after replacing the model or score artifacts with:

```bash
repath-eval calibrate \
  --base-config models/config_base.pkl \
  --config-output models/config.pkl \
  --output results/calibration_auto
```

The command reports accepted and correct cases, precision, conditional and end-to-end coverage, conditional and end-to-end recall, and both F1 definitions. Threshold selection never uses held-out test results.

## Latest REPATH research results

These tables were extracted from the three latest supplied notebook runs. They use the 50-feature representation, 16 development sites, six held-out test sites, four-fold site-grouped development cross-validation, and all 31 non-empty feature-group combinations.

> **Artifact alignment:** the bundled `models/lgb_ranker.txt`, `models/config_base.pkl`, calibration score files, and query manifest come from the latest supplied notebook run and align with the result tables below.

### Candidate retrieval

| Split       | Framework queries | Positive retained | Candidate recall | Mean shortlist | Pair rows |
| ----------- | ----------------: | ----------------: | ---------------: | -------------: | --------: |
| Development |               782 |               781 |           99.87% |          25.05 |     19568 |
| Test        |               318 |               314 |           98.74% |          25.01 |      7852 |

### Ranking performance

| Split                     | Framework | Retrievable | Candidate recall | Conditional Top-1 | Conditional MRR | Conditional Hit@3 | Conditional Hit@5 | End-to-end Top-1 | End-to-end MRR | End-to-end NDCG@5 |
| ------------------------- | --------: | ----------: | ---------------: | ----------------: | --------------: | ----------------: | ----------------: | ---------------: | -------------: | ----------------: |
| Development four-fold OOF |       782 |         781 |           99.87% |            98.08% |          98.77% |            99.62% |            99.74% |           97.95% |         98.64% |            98.88% |
| Held-out test             |       318 |         314 |           98.74% |            96.18% |          97.61% |            99.04% |            99.36% |           94.97% |         96.38% |            96.77% |

### Held-out test performance by site

| Test site         | Framework | Retrievable | Candidate recall | Conditional Top-1 | End-to-end Top-1 | End-to-end MRR | End-to-end NDCG@5 |
| ----------------- | --------: | ----------: | ---------------: | ----------------: | ---------------: | -------------: | ----------------: |
| beijing-2017-2019 |       103 |         103 |          100.00% |           100.00% |          100.00% |        100.00% |           100.00% |
| book-2016-2019    |       107 |         107 |          100.00% |           100.00% |          100.00% |        100.00% |           100.00% |
| yahoo             |        18 |          18 |          100.00% |            94.44% |           94.44% |         97.22% |            97.95% |
| movie-2014-2019   |        34 |          33 |           97.06% |            93.94% |           91.18% |         94.12% |            94.89% |
| instagram         |        12 |          12 |          100.00% |            83.33% |           83.33% |         90.28% |            92.76% |
| xfinity-2018-2020 |        44 |          41 |           93.18% |            82.93% |           77.27% |         82.20% |            83.39% |

### Confidence-margin operating point

The development OOF selector chose `tau = 0.40` while targeting 99% precision and at least 80% end-to-end coverage.

| Split                     |  Tau | Accepted | Correct | Precision | Conditional coverage | End-to-end coverage | Conditional recall | End-to-end recall | Conditional F1 | End-to-end F1 |
| ------------------------- | ---: | -------: | ------: | --------: | -------------------: | ------------------: | -----------------: | ----------------: | -------------: | ------------: |
| Development four-fold OOF | 0.40 |      764 |     757 |    99.08% |               97.82% |              97.70% |             96.93% |            96.80% |         97.99% |        97.93% |
| Held-out test             | 0.40 |      303 |     298 |    98.35% |               96.50% |              95.28% |             94.90% |            93.71% |         96.60% |        95.97% |

<details>
<summary><strong>Complete development OOF tau sweep</strong></summary>

|  Tau | Accepted | Correct | Precision | End-to-end coverage | End-to-end recall | End-to-end F1 |
| ---: | -------: | ------: | --------: | ------------------: | ----------------: | ------------: |
| 0.00 |      781 |     766 |    98.08% |              99.87% |            97.95% |        98.02% |
| 0.05 |      778 |     765 |    98.33% |              99.49% |            97.83% |        98.08% |
| 0.10 |      773 |     764 |    98.84% |              98.85% |            97.70% |        98.26% |
| 0.15 |      772 |     763 |    98.83% |              98.72% |            97.57% |        98.20% |
| 0.20 |      771 |     763 |    98.96% |              98.59% |            97.57% |        98.26% |
| 0.25 |      770 |     762 |    98.96% |              98.47% |            97.44% |        98.20% |
| 0.30 |      767 |     759 |    98.96% |              98.08% |            97.06% |        98.00% |
| 0.35 |      765 |     757 |    98.95% |              97.83% |            96.80% |        97.87% |
| 0.40 |      764 |     757 |    99.08% |              97.70% |            96.80% |        97.93% |
| 0.45 |      764 |     757 |    99.08% |              97.70% |            96.80% |        97.93% |
| 0.50 |      763 |     756 |    99.08% |              97.57% |            96.68% |        97.86% |
| 0.55 |      761 |     754 |    99.08% |              97.31% |            96.42% |        97.73% |
| 0.60 |      760 |     754 |    99.21% |              97.19% |            96.42% |        97.80% |
| 0.65 |      756 |     750 |    99.21% |              96.68% |            95.91% |        97.53% |
| 0.70 |      755 |     749 |    99.21% |              96.55% |            95.78% |        97.46% |
| 0.75 |      754 |     748 |    99.20% |              96.42% |            95.65% |        97.40% |
| 0.80 |      752 |     746 |    99.20% |              96.16% |            95.40% |        97.26% |
| 0.85 |      751 |     746 |    99.33% |              96.04% |            95.40% |        97.33% |
| 0.90 |      749 |     744 |    99.33% |              95.78% |            95.14% |        97.19% |
| 0.95 |      746 |     743 |    99.60% |              95.40% |            95.01% |        97.25% |
| 1.00 |      744 |     741 |    99.60% |              95.14% |            94.76% |        97.12% |

</details>

### Grouped feature importance

| Rank | Feature group | Features |      Gain | Gain share |
| ---: | ------------- | -------: | --------: | ---------: |
|    1 | Semantic      |        5 | 29573.244 |     55.79% |
|    2 | Lexical       |       12 | 18855.804 |     35.57% |
|    3 | Attribute     |       20 |  2092.700 |      3.95% |
|    4 | Structural    |        8 |  1261.093 |      2.38% |
|    5 | Geometry      |        5 |  1227.907 |      2.32% |

### Individual feature importance from the latest notebook run

The latest notebook displayed its Top 20 gain-ranked features directly.

| Rank | Vector index | Feature                 | Group      |      Gain | Gain share |
| ---: | -----------: | ----------------------- | ---------- | --------: | ---------: |
|    1 |           12 | `semantic_sim`          | Semantic   | 22852.957 |     43.11% |
|    2 |           10 | `text_seqsim`           | Lexical    | 12876.604 |     24.29% |
|    3 |           16 | `context_text_sim`      | Semantic   |  3569.410 |      6.73% |
|    4 |            5 | `text_exact`            | Lexical    |  3262.501 |      6.15% |
|    5 |           14 | `sibling_text_sim`      | Semantic   |  1707.919 |      3.22% |
|    6 |           13 | `parent_text_sim`       | Semantic   |  1406.107 |      2.65% |
|    7 |           22 | `sibling_position_diff` | Structural |   988.328 |      1.86% |
|    8 |            6 | `text_substr`           | Lexical    |   971.036 |      1.83% |
|    9 |            0 | `idx_distance_log`      | Lexical    |   946.889 |      1.79% |
|   10 |           37 | `nearby_jaccard`        | Attribute  |   585.561 |      1.10% |
|   11 |           34 | `parent_seqsim`         | Attribute  |   456.066 |      0.86% |
|   12 |            4 | `text_len_ratio`        | Lexical    |   452.803 |      0.85% |
|   13 |           36 | `sibling_after_jaccard` | Attribute  |   421.175 |      0.79% |
|   14 |           46 | `geo_center_dist`       | Geometry   |   374.177 |      0.71% |
|   15 |           32 | `class_seqsim`          | Attribute  |   356.448 |      0.67% |
|   16 |           47 | `geo_size_ratio`        | Geometry   |   284.859 |      0.54% |
|   17 |           48 | `bbox_dx`               | Geometry   |   271.531 |      0.51% |
|   18 |           45 | `geo_iou`               | Geometry   |   202.548 |      0.38% |
|   19 |           18 | `dom_depth_norm_diff`   | Structural |   134.391 |      0.25% |
|   20 |           33 | `ancestor_jaccard`      | Attribute  |   132.591 |      0.25% |

<details>
<summary><strong>Complete ordered 50-feature vector</strong></summary>

| Vector index | Feature                    | Group      | Type      | Semantic model   |
| -----------: | -------------------------- | ---------- | --------- | ---------------- |
|            0 | `idx_distance_log`         | Lexical    | `float32` |                  |
|            1 | `old_text_len`             | Lexical    | `float32` |                  |
|            2 | `new_text_len`             | Lexical    | `float32` |                  |
|            3 | `len_diff`                 | Lexical    | `float32` |                  |
|            4 | `text_len_ratio`           | Lexical    | `float32` |                  |
|            5 | `text_exact`               | Lexical    | `float32` |                  |
|            6 | `text_substr`              | Lexical    | `float32` |                  |
|            7 | `old_text_empty`           | Lexical    | `float32` |                  |
|            8 | `new_text_empty`           | Lexical    | `float32` |                  |
|            9 | `text_token_overlap`       | Lexical    | `float32` |                  |
|           10 | `text_seqsim`              | Lexical    | `float32` |                  |
|           11 | `n_candidates`             | Lexical    | `float32` |                  |
|           12 | `semantic_sim`             | Semantic   | `float32` | all-MiniLM-L6-v2 |
|           13 | `parent_text_sim`          | Semantic   | `float32` | all-MiniLM-L6-v2 |
|           14 | `sibling_text_sim`         | Semantic   | `float32` | all-MiniLM-L6-v2 |
|           15 | `child_text_sim`           | Semantic   | `float32` | all-MiniLM-L6-v2 |
|           16 | `context_text_sim`         | Semantic   | `float32` | all-MiniLM-L6-v2 |
|           17 | `tag_match`                | Structural | `float32` |                  |
|           18 | `dom_depth_norm_diff`      | Structural | `float32` |                  |
|           19 | `parent_chain_similarity`  | Structural | `float32` |                  |
|           20 | `ancestor_path_similarity` | Structural | `float32` |                  |
|           21 | `xpath_token_sim`          | Structural | `float32` |                  |
|           22 | `sibling_position_diff`    | Structural | `float32` |                  |
|           23 | `sibling_context_jaccard`  | Structural | `float32` |                  |
|           24 | `child_tag_jaccard`        | Structural | `float32` |                  |
|           25 | `label_seqsim`             | Attribute  | `float32` |                  |
|           26 | `heading_seqsim`           | Attribute  | `float32` |                  |
|           27 | `aria_seqsim`              | Attribute  | `float32` |                  |
|           28 | `placeholder_seqsim`       | Attribute  | `float32` |                  |
|           29 | `title_seqsim`             | Attribute  | `float32` |                  |
|           30 | `id_seqsim`                | Attribute  | `float32` |                  |
|           31 | `name_seqsim`              | Attribute  | `float32` |                  |
|           32 | `class_seqsim`             | Attribute  | `float32` |                  |
|           33 | `ancestor_jaccard`         | Attribute  | `float32` |                  |
|           34 | `parent_seqsim`            | Attribute  | `float32` |                  |
|           35 | `sibling_before_jaccard`   | Attribute  | `float32` |                  |
|           36 | `sibling_after_jaccard`    | Attribute  | `float32` |                  |
|           37 | `nearby_jaccard`           | Attribute  | `float32` |                  |
|           38 | `role_match`               | Attribute  | `float32` |                  |
|           39 | `type_match`               | Attribute  | `float32` |                  |
|           40 | `visible_match`            | Attribute  | `float32` |                  |
|           41 | `enabled_match`            | Attribute  | `float32` |                  |
|           42 | `id_subset`                | Attribute  | `float32` |                  |
|           43 | `dataTestId_subset`        | Attribute  | `float32` |                  |
|           44 | `attr_subset_any`          | Attribute  | `float32` |                  |
|           45 | `geo_iou`                  | Geometry   | `float32` |                  |
|           46 | `geo_center_dist`          | Geometry   | `float32` |                  |
|           47 | `geo_size_ratio`           | Geometry   | `float32` |                  |
|           48 | `bbox_dx`                  | Geometry   | `float32` |                  |
|           49 | `bbox_dy`                  | Geometry   | `float32` |                  |

</details>

<details>
<summary><strong>Complete 50-feature gain importance for the latest model</strong></summary>

| Rank | Vector index | Feature                    | Group      |      Gain | Gain share |
| ---: | -----------: | -------------------------- | ---------- | --------: | ---------: |
|    1 |           12 | `semantic_sim`             | Semantic   | 22852.957 |     43.11% |
|    2 |           10 | `text_seqsim`              | Lexical    | 12876.604 |     24.29% |
|    3 |           16 | `context_text_sim`         | Semantic   |  3569.410 |      6.73% |
|    4 |            5 | `text_exact`               | Lexical    |  3262.501 |      6.15% |
|    5 |           14 | `sibling_text_sim`         | Semantic   |  1707.919 |      3.22% |
|    6 |           13 | `parent_text_sim`          | Semantic   |  1406.107 |      2.65% |
|    7 |           22 | `sibling_position_diff`    | Structural |   988.328 |      1.86% |
|    8 |            6 | `text_substr`              | Lexical    |   971.036 |      1.83% |
|    9 |            0 | `idx_distance_log`         | Lexical    |   946.889 |      1.79% |
|   10 |           37 | `nearby_jaccard`           | Attribute  |   585.561 |      1.10% |
|   11 |           34 | `parent_seqsim`            | Attribute  |   456.066 |      0.86% |
|   12 |            4 | `text_len_ratio`           | Lexical    |   452.803 |      0.85% |
|   13 |           36 | `sibling_after_jaccard`    | Attribute  |   421.175 |      0.79% |
|   14 |           46 | `geo_center_dist`          | Geometry   |   374.177 |      0.71% |
|   15 |           32 | `class_seqsim`             | Attribute  |   356.448 |      0.67% |
|   16 |           47 | `geo_size_ratio`           | Geometry   |   284.859 |      0.54% |
|   17 |           48 | `bbox_dx`                  | Geometry   |   271.531 |      0.51% |
|   18 |           45 | `geo_iou`                  | Geometry   |   202.548 |      0.38% |
|   19 |           18 | `dom_depth_norm_diff`      | Structural |   134.391 |      0.25% |
|   20 |           33 | `ancestor_jaccard`         | Attribute  |   132.591 |      0.25% |
|   21 |            9 | `text_token_overlap`       | Lexical    |   108.140 |      0.20% |
|   22 |            2 | `new_text_len`             | Lexical    |   105.403 |      0.20% |
|   23 |           49 | `bbox_dy`                  | Geometry   |    94.791 |      0.18% |
|   24 |           24 | `child_tag_jaccard`        | Structural |    63.329 |      0.12% |
|   25 |           44 | `attr_subset_any`          | Attribute  |    58.702 |      0.11% |
|   26 |            3 | `len_diff`                 | Lexical    |    58.241 |      0.11% |
|   27 |            1 | `old_text_len`             | Lexical    |    52.799 |      0.10% |
|   28 |           35 | `sibling_before_jaccard`   | Attribute  |    49.914 |      0.09% |
|   29 |           19 | `parent_chain_similarity`  | Structural |    47.714 |      0.09% |
|   30 |           15 | `child_text_sim`           | Semantic   |    36.851 |      0.07% |
|   31 |            8 | `new_text_empty`           | Lexical    |    21.333 |      0.04% |
|   32 |           23 | `sibling_context_jaccard`  | Structural |    13.579 |      0.03% |
|   33 |           42 | `id_subset`                | Attribute  |     8.519 |      0.02% |
|   34 |           26 | `heading_seqsim`           | Attribute  |     8.115 |      0.02% |
|   35 |           21 | `xpath_token_sim`          | Structural |     7.572 |      0.01% |
|   36 |           20 | `ancestor_path_similarity` | Structural |     6.180 |      0.01% |
|   37 |           29 | `title_seqsim`             | Attribute  |     5.927 |      0.01% |
|   38 |           30 | `id_seqsim`                | Attribute  |     5.305 |      0.01% |
|   39 |           38 | `role_match`               | Attribute  |     3.997 |      0.01% |
|   40 |           27 | `aria_seqsim`              | Attribute  |     0.370 |      0.00% |
|   41 |           11 | `n_candidates`             | Lexical    |     0.056 |      0.00% |
|   42 |           31 | `name_seqsim`              | Attribute  |     0.011 |      0.00% |
|   43 |            7 | `old_text_empty`           | Lexical    |     0.000 |      0.00% |
|   44 |           17 | `tag_match`                | Structural |     0.000 |      0.00% |
|   45 |           25 | `label_seqsim`             | Attribute  |     0.000 |      0.00% |
|   46 |           28 | `placeholder_seqsim`       | Attribute  |     0.000 |      0.00% |
|   47 |           39 | `type_match`               | Attribute  |     0.000 |      0.00% |
|   48 |           40 | `visible_match`            | Attribute  |     0.000 |      0.00% |
|   49 |           41 | `enabled_match`            | Attribute  |     0.000 |      0.00% |
|   50 |           43 | `dataTestId_subset`        | Attribute  |     0.000 |      0.00% |

</details>

### Exhaustive feature-group ablation

<details open>
<summary><strong>Complete 31-combination ablation table</strong></summary>

| Rank | Included feature groups                                | Features | CV rounds | Test end-to-end Top-1 | Test end-to-end MRR | Test end-to-end NDCG@5 | Δ Top-1 vs full |
| ---: | ------------------------------------------------------ | -------: | --------: | --------------------: | ------------------: | ---------------------: | --------------: |
|    1 | lexical + semantic + structural + attribute + geometry |       50 |       120 |                94.97% |              96.38% |                 96.77% |        +0.00 pp |
|    2 | lexical + semantic + structural + geometry             |       30 |        30 |                94.65% |              96.07% |                 96.40% |        -0.31 pp |
|    3 | lexical + semantic + structural + attribute            |       45 |        65 |                94.34% |              95.88% |                 96.37% |        -0.63 pp |
|    4 | lexical + semantic + attribute + geometry              |       42 |        46 |                93.40% |              95.37% |                 96.00% |        -1.57 pp |
|    5 | lexical + semantic + attribute                         |       37 |       103 |                93.40% |              95.39% |                 96.00% |        -1.57 pp |
|    6 | lexical + semantic + structural                        |       25 |        22 |                93.08% |              95.10% |                 95.71% |        -1.89 pp |
|    7 | lexical + semantic + geometry                          |       22 |        80 |                93.08% |              94.99% |                 95.61% |        -1.89 pp |
|    8 | semantic + structural + geometry                       |       18 |        40 |                92.14% |              94.60% |                 95.45% |        -2.83 pp |
|    9 | semantic + structural + attribute + geometry           |       38 |        84 |                92.14% |              94.74% |                 95.44% |        -2.83 pp |
|   10 | lexical + structural + attribute + geometry            |       45 |        49 |                91.51% |              93.80% |                 94.59% |        -3.46 pp |
|   11 | semantic + structural                                  |       13 |        46 |                90.88% |              93.66% |                 94.52% |        -4.09 pp |
|   12 | lexical + structural + attribute                       |       40 |        82 |                90.25% |              92.93% |                 94.06% |        -4.72 pp |
|   13 | lexical + structural + geometry                        |       25 |        52 |                89.94% |              92.64% |                 93.27% |        -5.03 pp |
|   14 | lexical + attribute                                    |       32 |        73 |                89.94% |              92.34% |                 93.27% |        -5.03 pp |
|   15 | lexical + semantic                                     |       17 |        21 |                89.62% |              93.45% |                 94.47% |        -5.35 pp |
|   16 | semantic + structural + attribute                      |       33 |        32 |                89.31% |              92.79% |                 93.90% |        -5.66 pp |
|   17 | lexical + attribute + geometry                         |       37 |        69 |                89.31% |              92.15% |                 92.91% |        -5.66 pp |
|   18 | semantic + geometry                                    |       10 |        89 |                88.68% |              92.70% |                 93.80% |        -6.29 pp |
|   19 | semantic + attribute                                   |       25 |        50 |                88.68% |              92.21% |                 93.23% |        -6.29 pp |
|   20 | semantic + attribute + geometry                        |       30 |        60 |                88.36% |              92.66% |                 93.99% |        -6.60 pp |
|   21 | lexical + structural                                   |       20 |        76 |                88.36% |              91.99% |                 93.47% |        -6.60 pp |
|   22 | lexical + geometry                                     |       17 |        72 |                87.42% |              90.84% |                 91.69% |        -7.55 pp |
|   23 | semantic                                               |        5 |        68 |                84.28% |              90.10% |                 91.68% |       -10.69 pp |
|   24 | lexical                                                |       12 |        36 |                78.62% |              84.82% |                 85.99% |       -16.35 pp |
|   25 | structural + attribute + geometry                      |       33 |       116 |                64.47% |              74.24% |                 76.92% |       -30.50 pp |
|   26 | attribute + geometry                                   |       25 |       109 |                59.12% |              68.46% |                 70.52% |       -35.85 pp |
|   27 | structural + geometry                                  |       13 |        32 |                58.80% |              68.82% |                 71.14% |       -36.16 pp |
|   28 | structural + attribute                                 |       28 |        98 |                57.55% |              70.12% |                 74.06% |       -37.42 pp |
|   29 | structural                                             |        8 |        10 |                49.06% |              63.99% |                 68.20% |       -45.91 pp |
|   30 | geometry                                               |        5 |        88 |                48.11% |              58.96% |                 60.04% |       -46.86 pp |
|   31 | attribute                                              |       20 |        60 |                32.39% |              47.04% |                 48.34% |       -62.58 pp |

</details>

## Output files

A benchmark run writes `query_results.csv`, `site_results.csv`, `summary.csv`, and `run_metadata.json`. Runtime fields appear only with `--measure-runtime`.

A calibration run writes `tau_margin_summary.csv`, `tau_margin_query_decisions.csv`, and `calibration_metadata.json`. Automatic selection also writes `tau_margin_development_oof_curve.csv`.

## Evaluation protocol

The benchmark reads each site's `result/result.json` and uses `matchMap` as the expected old-to-new mapping. Queries whose old grouped node cannot be resolved, or whose old grouped node has `elementType == 1`, are excluded before evaluation. Every remaining query stays in the denominator. A missing prediction, failed match, or algorithm error is incorrect.

Top-1 correctness requires exact equality between the predicted and expected new grouped-node IDs. Fast execution reuses page-level preparation only to reduce execution time; it does not intentionally alter candidates, scores, rankings, predictions, or correctness.

## Baseline attribution and implementation sources

Each implementation is pinned to an authors' repository revision. The revisions are also recorded in every `run_metadata.json` file.

### WATER

- Paper: Shauvik Roy Choudhary, Dan Zhao, Husayn Versee, and Alessandro Orso, ["WATER: Web Application TEst Repair"](https://doi.org/10.1145/2002931.2002935), 2011.
- Authors' repository: [`shauvik/water`](https://github.com/shauvik/water)
- Pinned revision: [`c57311e56afb8e52ccd315e460e1a6f5084a7b95`](https://github.com/shauvik/water/tree/c57311e56afb8e52ccd315e460e1a6f5084a7b95)
- Benchmark boundary: WATER's candidate construction and similarity calculation are retained. The original implementation validates candidate repairs by rerunning a modified browser test; this benchmark instead returns deterministic candidate predictions for the fixed query-level protocol.

### VISTA

- Paper: Andrea Stocco, Rahulkrishna Yandrapally, and Ali Mesbah, ["Visual Web Test Repair"](https://doi.org/10.1145/3236024.3236063), ESEC/FSE 2018.
- Authors' repository: [`saltlab/vista`](https://github.com/saltlab/vista)
- Pinned revision: [`7bf2a588897637e0e1c9a2cc33e4d372a62bcaf0`](https://github.com/saltlab/vista/tree/7bf2a588897637e0e1c9a2cc33e4d372a62bcaf0)
- Benchmark boundary: the crop construction, SIFT/FAST feature checks, normalized template matching, and smallest-containing-element selection follow the pinned implementation. Numerical results can vary from the original Java/OpenCV environment because this package uses current Python OpenCV.

### SFTM

- Paper: Sacha Brisset, Romain Rouvoy, Renaud Pawlak, and Lionel Seinturier, ["SFTM: Fast Comparison of Web Documents using Similarity-based Flexible Tree Matching"](https://arxiv.org/abs/2004.12821), 2020.
- Authors' repository: [`amaris/sftm_tree_matching`](https://github.com/amaris/sftm_tree_matching)
- Pinned revision: [`4f8683b0e5a21050d1679f1c350f558a5a4171e5`](https://github.com/amaris/sftm_tree_matching/tree/4f8683b0e5a21050d1679f1c350f558a5a4171e5)
- Benchmark boundary: the source defaults, tokenization, indexing, similarity propagation, no-match edges, and one-iteration greedy matching behavior are retained. BeautifulSoup replaces Jsoup for HTML parsing; when an archived HTML file is unavailable, captured DOM metadata is used to construct the tree.

### WebEvo

- Paper: Fei Shao, Rui Xu, Wasif Haque, Jingwei Xu, Ying Zhang, Wei Yang, Yanfang Ye, and Xusheng Xiao, ["WebEvo: Taming Web Application Evolution via Detecting Semantic Structure Changes"](https://doi.org/10.1145/3460319.3464800), ISSTA 2021.
- Authors' repository: [`webevoexp/webevo`](https://github.com/webevoexp/webevo)
- Pinned revision: [`d195630b8dd5d85790d5aebb5c81c29bd03f01ca`](https://github.com/webevoexp/webevo/tree/d195630b8dd5d85790d5aebb5c81c29bd03f01ca)
- Benchmark boundary: this package implements WebEvo's semantics-based visual-search module: tag-ordered candidates, text-based shortlist, 16×16 perceptual fingerprint, grayscale/inversion stages, and the 0.60 threshold. The fixed UITestFix queries replace WebEvo's separate history and DOM-change discovery stages, and stored element screenshots replace live Selenium screenshot cropping.

### Similo

- Paper: Michel Nass, Emil Alégroth, Robert Feldt, Maurizio Leotta, and Filippo Ricca, ["Similarity-based Web Element Localization for Robust Test Automation"](https://doi.org/10.1145/3571855), ACM TOSEM, 2023.
- Authors' repository: [`michelnass/Similo2`](https://github.com/michelnass/Similo2)
- Pinned revision: [`743ddede7df92814ddc3fb7f96e09bdb508e285a`](https://github.com/michelnass/Similo2/tree/743ddede7df92814ddc3fb7f96e09bdb508e285a)
- Benchmark boundary: candidate eligibility and the original 14 manually weighted locator properties are retained. The authors' program returns the best candidate; this benchmark preserves all scored candidates so that the common evaluator can derive Top-k rankings while using the same Top-1 ordering.

## Comparing with external reference predictions

A CSV from another implementation can be compared with this suite's query-level predictions:

```bash
repath-eval compare \
  --python-results results/baselines/query_results.csv \
  --reference-results /path/to/reference_results.csv \
  --output results/parity_mismatches.csv
```

Both files must contain `algorithm`, `site`, `old_element_id`, and `predicted_new_element_id`.

## Third-party notices

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The SFTM module carries `SPDX-License-Identifier: GPL-3.0-or-later`, and the GPL version 3 text is included in [`LICENSES/GPL-3.0.txt`](LICENSES/GPL-3.0.txt).
