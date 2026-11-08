"""Validate the Potree 2 hierarchy and every referenced octree byte range."""
import json
import struct
from collections import deque
from pathlib import Path


def validate_potree(directory: Path, expected_points: int) -> Path:
    manifest = directory / "metadata.json"
    for name in ("metadata.json", "hierarchy.bin", "octree.bin"):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Potree output is missing or unsafe: {name}")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata.get("version") != "2.0" or metadata.get("points") != expected_points:
        raise RuntimeError("Potree metadata version/point count does not match PDAL")
    if expected_points <= 0:
        raise RuntimeError("Empty point clouds cannot produce a usable Potree viewer")
    attributes = metadata.get("attributes", [])
    stride = sum(attribute["size"] for attribute in attributes)
    if stride <= 0:
        raise RuntimeError("Potree point attributes are missing")
    hierarchy = directory / "hierarchy.bin"
    hierarchy_size = hierarchy.stat().st_size
    octree_size = (directory / "octree.bin").stat().st_size
    chunks = deque([(0, metadata["hierarchy"]["firstChunkSize"])])
    seen_chunks = set()
    data_ranges = []
    total_points = 0
    with hierarchy.open("rb") as source:
        while chunks:
            offset, size = chunks.popleft()
            if (offset, size) in seen_chunks or offset < 0 or size <= 0 or size % 22 or offset + size > hierarchy_size:
                raise RuntimeError("Potree hierarchy chunk is invalid or repeated")
            seen_chunks.add((offset, size))
            source.seek(offset)
            nodes = deque(["r"])
            for node_type, mask, count, byte_offset, byte_size in struct.iter_unpack("<BBIQQ", source.read(size)):
                if not nodes:
                    raise RuntimeError("Potree hierarchy contains unreachable nodes")
                name = nodes.popleft()
                if node_type == 2:
                    chunks.append((byte_offset, byte_size))
                    continue
                if node_type not in (0, 1):
                    raise RuntimeError("Potree hierarchy node type/children are invalid")
                if byte_offset + byte_size > octree_size or (count and not byte_size):
                    raise RuntimeError("Potree octree tile is truncated")
                if metadata.get("encoding", "DEFAULT") == "DEFAULT" and byte_size != count * stride:
                    raise RuntimeError("Potree octree tile size does not match point attributes")
                if byte_size:
                    data_ranges.append((byte_offset, byte_offset + byte_size))
                total_points += count
                nodes.extend(name + str(child) for child in range(8) if mask & (1 << child))
            if nodes:
                raise RuntimeError("Potree hierarchy is missing child nodes")
    if total_points != expected_points:
        raise RuntimeError("Potree hierarchy point total does not match PDAL")
    ranges = sorted(data_ranges)
    if any(current[0] < previous[1] for previous, current in zip(ranges, ranges[1:])):
        raise RuntimeError("Potree octree tile ranges overlap")
    return manifest
