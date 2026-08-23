import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from transformers import AutoModelForImageClassification

from config import TrainingConfig
from dataset import loader


def run(config: TrainingConfig) -> None:
    random.seed(config.seed); np.random.seed(config.seed); torch.manual_seed(config.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_loader, classes = loader(config.dataset_path, "train", config.batch_size, config.num_workers, True)
    val_loader, val_classes = loader(config.dataset_path, "val", config.batch_size, config.num_workers, False)
    if classes != val_classes or set(classes) != {"fake", "real"}:
        raise ValueError("train and val must each contain real/ and fake/ directories")
    id2label = {index: label for label, index in classes.items()}
    model = AutoModelForImageClassification.from_pretrained(
        config.model_name, num_labels=2, id2label=id2label, label2id=classes, ignore_mismatched_sizes=True
    ).to(device)
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=config.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")
    best, stale = float("inf"), 0
    output = Path(config.output_dir); output.mkdir(parents=True, exist_ok=True); config.save()
    for epoch in range(config.epochs):
        model.train()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=device == "cuda"):
                loss = model(pixel_values=images, labels=labels).loss
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
        model.eval(); losses = []
        with torch.inference_mode():
            for images, labels in val_loader:
                losses.append(float(model(pixel_values=images.to(device), labels=labels.to(device)).loss))
        val_loss = float(np.mean(losses)); scheduler.step()
        print(json.dumps({"epoch": epoch + 1, "validation_loss": val_loss}))
        if val_loss < best:
            best, stale = val_loss, 0
            model.save_pretrained(output / "best-checkpoint")
            (output / "class_labels.json").write_text(json.dumps(classes, indent=2), encoding="utf-8")
        else:
            stale += 1
            if stale >= config.patience: break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_path"); parser.add_argument("--output-dir", default="artifacts/experiment")
    parser.add_argument("--model-name", default="google/vit-base-patch16-224-in21k")
    parser.add_argument("--batch-size", type=int, default=16); parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=2e-5); parser.add_argument("--weight-decay", type=float, default=.01)
    parser.add_argument("--seed", type=int, default=42)
    run(TrainingConfig(**vars(parser.parse_args())))

