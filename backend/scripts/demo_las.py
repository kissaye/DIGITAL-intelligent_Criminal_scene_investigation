"""Create an original synthetic LAS 1.2 RGB grid, released under CC0-1.0.

No measured coordinates, people, locations, or case materials are included.
"""
import argparse
import struct
from pathlib import Path


def create_demo(path: Path) -> None:
    header = bytearray(227)
    header[:4] = b"LASF"
    header[24:26] = bytes([1, 2])
    header[26:58] = b"M7 synthetic grid".ljust(32, b"\0")
    header[58:90] = b"CC0-1.0 stdlib generator".ljust(32, b"\0")
    struct.pack_into("<HHHII", header, 90, 1, 2026, 227, 227, 0)
    header[104] = 2
    struct.pack_into("<HI", header, 105, 26, 1000)
    struct.pack_into("<5I", header, 111, 1000, 0, 0, 0, 0)
    struct.pack_into("<3d", header, 131, 0.01, 0.01, 0.01)
    struct.pack_into("<6d", header, 179, 9, 0, 9, 0, 9, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as target:
        target.write(header)
        for x in range(10):
            for y in range(10):
                for z in range(10):
                    target.write(struct.pack("<iiiHBBbBHHHH", x * 100, y * 100, z * 100,
                                             100, 9, 1, 0, 0, 0, x * 7000, y * 7000, z * 7000))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    create_demo(parser.parse_args().path)
