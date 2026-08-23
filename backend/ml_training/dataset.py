import io
import random

from PIL import Image
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from torchvision.transforms import v2


class RandomJpegCompression:
    def __init__(self, probability: float = 0.25) -> None:
        self.probability = probability

    def __call__(self, image: Image.Image) -> Image.Image:
        if random.random() >= self.probability:
            return image
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=random.randint(55, 95))
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")


def transforms(train: bool):
    common = [v2.ToImage(), v2.Resize((224, 224)), v2.ToDtype(__import__("torch").float32, scale=True), v2.Normalize([0.5] * 3, [0.5] * 3)]
    if not train:
        return v2.Compose(common)
    return v2.Compose([
        v2.RandomResizedCrop((224, 224), scale=(0.8, 1.0)),
        v2.RandomHorizontalFlip(),
        v2.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.08),
        RandomJpegCompression(),
        v2.ToImage(),
        v2.ToDtype(__import__("torch").float32, scale=True),
        v2.Normalize([0.5] * 3, [0.5] * 3),
    ])


def loader(path: str, split: str, batch_size: int, workers: int, shuffle: bool):
    dataset = ImageFolder(f"{path}/{split}", transform=transforms(split == "train"))
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=workers, pin_memory=True), dataset.class_to_idx

