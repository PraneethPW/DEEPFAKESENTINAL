import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar


def calibrate(input_path: str, output_path: str) -> None:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    logits, labels = np.asarray(data["logits"]), np.asarray(data["labels"])
    def loss(temperature):
        scaled = logits / temperature
        scaled -= scaled.max(axis=1, keepdims=True)
        probabilities = np.exp(scaled) / np.exp(scaled).sum(axis=1, keepdims=True)
        return -np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-9, 1)).mean()
    result = minimize_scalar(loss, bounds=(0.05, 10), method="bounded")
    Path(output_path).write_text(json.dumps({"temperature": float(result.x), "objective": float(result.fun)}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("output")
    args = parser.parse_args(); calibrate(args.input, args.output)

