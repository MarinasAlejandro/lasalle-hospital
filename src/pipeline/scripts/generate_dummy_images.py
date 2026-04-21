"""Generate dummy PNG radiography images for local testing and demos.

These are NOT medical data — just valid 1x1 PNG placeholders named with the
convention `{patient_external_id}_xray{n}.png`. Use this to exercise the
ingestion pipeline without depending on the real Kaggle dataset.

For training the actual ML model, download the real dataset — see
docs/runbooks/download-radiography-dataset.md.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)

# Minimal valid 1x1 RGBA PNG
PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A"
    "0000000D49484452"
    "00000001000000010806000000"
    "1F15C489"
    "0000000A49444154"
    "78DA63000100000500010D0A2DB4"
    "0000000049454E44"
    "AE426082"
)


def generate_dummy_images(
    output_dir: Path,
    n_patients: int = 20,
    images_per_patient_max: int = 3,
    seed: int | None = None,
) -> int:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for i in range(n_patients):
        patient_id = f"HOSP-{i:06d}"
        count = rng.randint(1, images_per_patient_max)
        for n in range(count):
            filename = f"{patient_id}_xray{n + 1}.png"
            (output_dir / filename).write_bytes(PNG_BYTES)
            total += 1

    logger.info("Generated %d dummy PNGs at %s", total, output_dir)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dummy PNG images")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/images"))
    parser.add_argument("--patients", type=int, default=20)
    parser.add_argument("--max-per-patient", type=int, default=3)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    generate_dummy_images(
        output_dir=args.output_dir,
        n_patients=args.patients,
        images_per_patient_max=args.max_per_patient,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
