# REPATH model artifacts

This directory contains artifacts from the latest supplied 50-feature training and calibration run:

- `lgb_ranker.txt`: final LightGBM LambdaRank model trained on all development sites.
- `config_base.pkl`: ordered feature schema, SBERT model name, training settings, split metadata, and ranking metrics for the same model run.
- `config.pkl`: calibrated configuration generated from `config_base.pkl`; it includes the selected confidence margin `tau = 0.40` and the associated development/test calibration metrics.

`lgb_ranker.txt` and `config_base.pkl` must always be replaced together when retraining. After replacement, regenerate `config.pkl` with `repath-eval calibrate --base-config models/config_base.pkl --config-output models/config.pkl`.
