from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class TrainingConfig:
    dataset_path: str
    output_dir: str = "artifacts/experiment"
    model_name: str = "google/vit-base-patch16-224-in21k"
    batch_size: int = 16
    epochs: int = 10
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    seed: int = 42
    patience: int = 3
    num_workers: int = 4

    def save(self) -> None:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "training_config.json").write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

