from statistics import mean, median

from app.ml.inference import classify


def aggregate_probabilities(values: list[float], minimum_valid: int = 3) -> dict:
    if len(values) < minimum_valid:
        return {
            "score": mean(values) if values else None,
            "classification": "INCONCLUSIVE",
            "method": "trimmed_mean",
            "warning": "Too few usable frames were available for a reliable aggregate.",
            "analysed_frames": len(values),
        }
    ordered = sorted(values)
    trim = int(len(ordered) * 0.1) if len(ordered) >= 10 else 0
    robust = ordered[trim : len(ordered) - trim] if trim else ordered
    score = float(mean(robust))
    return {
        "score": score,
        "classification": classify(score),
        "method": "trimmed_mean",
        "mean": float(mean(values)),
        "median": float(median(values)),
        "minimum": float(min(values)),
        "maximum": float(max(values)),
        "high_score_frames": sum(value >= 0.65 for value in values),
        "analysed_frames": len(values),
    }

