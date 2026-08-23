import math

import cv2
import numpy as np
import torch
from PIL import Image


def attention_rollout(attentions: tuple[torch.Tensor, ...], image_size: tuple[int, int]) -> np.ndarray:
    if not attentions:
        raise ValueError("model did not return attention tensors")
    matrices = []
    for attention in attentions:
        layer = attention.detach().float().cpu().mean(dim=1)[0]
        identity = torch.eye(layer.shape[-1])
        layer = (layer + identity) / 2
        layer = layer / layer.sum(dim=-1, keepdim=True).clamp_min(1e-8)
        matrices.append(layer)
    rollout = matrices[0]
    for layer in matrices[1:]:
        rollout = layer @ rollout
    patch_values = rollout[0, 1:].numpy()
    token_count = patch_values.size
    grid_h = int(math.sqrt(token_count))
    while grid_h > 1 and token_count % grid_h:
        grid_h -= 1
    grid_w = token_count // grid_h
    if grid_h * grid_w != token_count:
        raise ValueError("attention patch tokens cannot be mapped to a spatial grid")
    mask = patch_values.reshape(grid_h, grid_w)
    mask -= mask.min()
    peak = mask.max()
    if peak > 0:
        mask /= peak
    resized = cv2.resize(mask, image_size, interpolation=cv2.INTER_CUBIC)
    return np.clip(resized, 0.0, 1.0)


def render_evidence(image: Image.Image, mask: np.ndarray) -> tuple[Image.Image, Image.Image, Image.Image]:
    rgb = np.asarray(image.convert("RGB"))
    mask_u8 = np.clip(mask * 255, 0, 255).astype(np.uint8)
    heat_bgr = cv2.applyColorMap(mask_u8, cv2.COLORMAP_TURBO)
    heat_rgb = cv2.cvtColor(heat_bgr, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(rgb, 0.58, heat_rgb, 0.42, 0)
    return Image.fromarray(mask_u8), Image.fromarray(heat_rgb), Image.fromarray(overlay)
