# Reproducible ViT experimentation

Prepare only licensed data using `dataset/{train,val,test}/{real,fake}`. Run `python train.py dataset --output-dir artifacts/run-01`, then `python evaluate.py artifacts/run-01/best-checkpoint dataset`. No metric is committed or displayed until evaluation produces it. Keep people or manipulation sources separated across splits to reduce identity leakage.

The training augmentations model moderate crop, color, flip, and compression variation without applying class-specific artifacts. For research-grade claims, report per-source and per-compression results, data provenance, confidence intervals, and out-of-distribution tests.

