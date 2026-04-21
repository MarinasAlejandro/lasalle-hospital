"""Tests for IncomingFilesWatcher: reacts to CSVs landing in an incoming dir."""
from __future__ import annotations

import csv
import threading
import time
from pathlib import Path

import pytest

from src.pipeline.watcher import IncomingFilesWatcher


def _write_patients(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["external_id", "name", "birth_date", "gender", "blood_type"])
        w.writerow(["HOSP-000001", "Ana", "1980-05-12", "F", "A+"])


def _write_admissions(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "patient_external_id", "admission_date", "discharge_date",
            "department", "diagnosis_code", "diagnosis_description", "status",
        ])
        w.writerow(["HOSP-000001", "2025-03-10", "", "UCI", "J18.9", "Pneumonia", "admitted"])


@pytest.fixture
def incoming_dir(tmp_path: Path) -> Path:
    d = tmp_path / "incoming"
    d.mkdir()
    (d / "processed").mkdir()
    return d


def test_watcher_triggers_callback_when_both_csvs_land(incoming_dir: Path):
    """When patients.csv and admissions.csv both appear, the callback fires."""
    triggered = threading.Event()
    received_paths: dict[str, Path] = {}

    def on_ready(patients_csv: Path, admissions_csv: Path) -> None:
        received_paths["patients"] = patients_csv
        received_paths["admissions"] = admissions_csv
        triggered.set()

    watcher = IncomingFilesWatcher(incoming_dir=incoming_dir, on_ready=on_ready)
    watcher.start()
    try:
        _write_patients(incoming_dir / "patients.csv")
        _write_admissions(incoming_dir / "admissions.csv")

        assert triggered.wait(timeout=5.0), "Callback was not triggered within 5s"
        assert received_paths["patients"].name == "patients.csv"
        assert received_paths["admissions"].name == "admissions.csv"
    finally:
        watcher.stop()


def test_watcher_moves_files_to_processed_after_callback(incoming_dir: Path):
    triggered = threading.Event()

    def on_ready(*_args) -> None:
        triggered.set()

    watcher = IncomingFilesWatcher(incoming_dir=incoming_dir, on_ready=on_ready)
    watcher.start()
    try:
        _write_patients(incoming_dir / "patients.csv")
        _write_admissions(incoming_dir / "admissions.csv")

        assert triggered.wait(timeout=5.0)
        # Give the watcher a moment to perform the move after the callback
        time.sleep(0.5)

        assert not (incoming_dir / "patients.csv").exists()
        assert not (incoming_dir / "admissions.csv").exists()
        assert (incoming_dir / "processed" / "patients.csv").exists()
        assert (incoming_dir / "processed" / "admissions.csv").exists()
    finally:
        watcher.stop()


def test_watcher_does_not_trigger_with_only_one_csv(incoming_dir: Path):
    triggered = threading.Event()

    def on_ready(*_args) -> None:
        triggered.set()

    watcher = IncomingFilesWatcher(incoming_dir=incoming_dir, on_ready=on_ready)
    watcher.start()
    try:
        _write_patients(incoming_dir / "patients.csv")
        assert not triggered.wait(timeout=1.0), "Should wait for admissions.csv too"
    finally:
        watcher.stop()


def test_watcher_raises_when_incoming_dir_missing(tmp_path: Path):
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        IncomingFilesWatcher(
            incoming_dir=missing,
            on_ready=lambda *_a: None,
        )
