"""Regression tests for PotreeConverter publication asset filtering."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes.m5 import copy_checksum, copy_teaching_assets, safe_potree_source


def source(tmp_path, *, log=False):
    root = tmp_path / "storage"; potree = root / "cases" / "case" / "versions" / "version" / "potree"
    potree.mkdir(parents=True)
    for name in ("metadata.json", "hierarchy.bin", "octree.bin"):
        (potree / name).write_bytes(name.encode())
    if log: (potree / "log.txt").write_text("converter diagnostics")
    return root, potree, SimpleNamespace(case_id="case", id="version")


def valid(tmp_path, log=False):
    root, potree, version = source(tmp_path, log=log)
    return root, potree, version, safe_potree_source(version, root)


def test_required_assets_and_root_log_are_publishable(tmp_path):
    root, potree, version, (_, returned, assets) = valid(tmp_path, log=True)
    assert returned == potree
    assert Path("log.txt") not in assets
    assert {Path("metadata.json"), Path("hierarchy.bin"), Path("octree.bin")} <= set(assets)


def test_copy_omits_log_and_checksum_ignores_it(tmp_path):
    root, potree, version, (_, _, assets) = valid(tmp_path, log=True)
    destination = root / "teaching" / "copy"
    copy_teaching_assets(potree, destination, assets)
    before = copy_checksum(destination)
    (potree / "log.txt").write_text("changed diagnostics")
    assert not (destination / "log.txt").exists()
    assert copy_checksum(destination) == before
    assert all(path.suffix in {".json", ".bin"} for path in destination.rglob("*") if path.is_file())


@pytest.mark.parametrize("name", ["secret.txt", "nested/secret.txt", "tool.exe", "run.sh", "script.py"])
def test_unknown_files_are_rejected(tmp_path, name):
    root, potree, version = source(tmp_path)
    path = potree / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("x")
    with pytest.raises(HTTPException) as error: safe_potree_source(version, root)
    assert error.value.status_code == 409


@pytest.mark.parametrize("missing", ["metadata.json", "hierarchy.bin", "octree.bin"])
def test_missing_required_asset_is_rejected(tmp_path, missing):
    root, potree, version = source(tmp_path); (potree / missing).unlink()
    with pytest.raises(HTTPException) as error: safe_potree_source(version, root)
    assert error.value.status_code == 409


def test_nested_assets_preserve_relative_paths_and_checksum_uses_path(tmp_path):
    root, potree, version = source(tmp_path)
    nested = potree / "nested"; nested.mkdir(); (nested / "tile.bin").write_bytes(b"payload")
    _, _, assets = safe_potree_source(version, root)
    first = root / "teaching" / "one"; copy_teaching_assets(potree, first, assets)
    assert (first / "nested" / "tile.bin").read_bytes() == b"payload"
    second = root / "teaching" / "two"; second.mkdir(); (second / "renamed.bin").write_bytes(b"payload")
    assert copy_checksum(first) != copy_checksum(second)


def test_symlinks_and_existing_destination_are_rejected(tmp_path):
    root, potree, version = source(tmp_path)
    target = potree / "metadata.json"; link = potree / "nested-link.bin"
    try: link.symlink_to(target)
    except OSError: pytest.skip("symlinks unavailable")
    with pytest.raises(HTTPException): safe_potree_source(version, root)
    link.unlink()
    _, _, assets = safe_potree_source(version, root)
    destination = root / "teaching" / "existing"; destination.mkdir(parents=True)
    with pytest.raises(HTTPException): copy_teaching_assets(potree, destination, assets)


def test_required_asset_symlink_is_rejected(tmp_path):
    root, potree, version = source(tmp_path)
    metadata = potree / "metadata.json"
    try:
        metadata.unlink()
        metadata.symlink_to(potree / "hierarchy.bin")
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(HTTPException) as error:
        safe_potree_source(version, root)
    assert error.value.status_code == 409


def test_non_regular_fifo_is_rejected_when_supported(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFOs unavailable on this platform")
    root, potree, version = source(tmp_path)
    os.mkfifo(potree / "stream.bin")
    with pytest.raises(HTTPException) as error:
        safe_potree_source(version, root)
    assert error.value.status_code == 409


def test_copy_failure_does_not_overwrite_existing_files(tmp_path, monkeypatch):
    root, potree, version = source(tmp_path); _, _, assets = safe_potree_source(version, root)
    destination = root / "teaching" / "copy"
    original = __import__("shutil").copy2
    calls = {"count": 0}
    def fail_second(src, dst):
        calls["count"] += 1
        if calls["count"] == 2: raise OSError("simulated copy failure")
        return original(src, dst)
    monkeypatch.setattr("app.api.routes.m5.shutil.copy2", fail_second)
    with pytest.raises(OSError): copy_teaching_assets(potree, destination, assets)
    assert not destination.exists()
