import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForImageClassification

from dataset import loader
from metrics import classification_metrics


def evaluate(model_path: str, dataset_path: str, output: str) -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    data, classes = loader(dataset_path, "test", 32, 2, False)
    fake_id = classes.get("fake")
    if fake_id is None: raise ValueError("test/fake directory is required")
    model = AutoModelForImageClassification.from_pretrained(model_path).to(device).eval()
    targets, predictions, fake_scores = [], [], []
    with torch.inference_mode():
        for images, labels in data:
            probabilities = torch.softmax(model(pixel_values=images.to(device)).logits, dim=-1).cpu()
            targets.extend(labels.tolist()); predictions.extend(probabilities.argmax(1).tolist()); fake_scores.extend(probabilities[:, fake_id].tolist())
    result = classification_metrics(targets, predictions, fake_scores)
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("model_path"); parser.add_argument("dataset_path"); parser.add_argument("--output", default="evaluation.json")
    args = parser.parse_args(); evaluate(args.model_path, args.dataset_path, args.output)

