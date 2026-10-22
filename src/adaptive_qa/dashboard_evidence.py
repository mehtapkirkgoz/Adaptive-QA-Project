"""Bounded PNG import from trusted local screenshot output; no client paths."""

import os
from pathlib import Path
import re
import stat
import struct
import zlib


MAX_PNG_BYTES = 5 * 1024 * 1024


def validate_png(data):
    if not isinstance(data, bytes) or not 45 <= len(data) <= MAX_PNG_BYTES or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('A bounded PNG is required.')
    position, chunks, image_data = 8, 0, False
    while position + 12 <= len(data) and chunks < 10000:
        size = int.from_bytes(data[position:position + 4], 'big')
        kind = data[position + 4:position + 8]
        end = position + 12 + size
        if end > len(data) or not re.fullmatch(b'[A-Za-z]{4}', kind):
            raise ValueError('Invalid PNG chunk.')
        if kind not in (b'IHDR', b'IDAT', b'IEND', b'PLTE', b'tRNS', b'sRGB', b'gAMA', b'cHRM', b'pHYs'):
            raise ValueError('Unsupported screenshot metadata or animation.')
        payload = data[position + 8:position + 8 + size]
        crc = int.from_bytes(data[end - 4:end], 'big')
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError('Invalid PNG checksum.')
        if chunks == 0:
            if kind != b'IHDR' or size != 13:
                raise ValueError('PNG header is required.')
            width, height = struct.unpack('>II', payload[:8])
            if not 0 < width <= 20000 or not 0 < height <= 20000 or width * height > 40000000:
                raise ValueError('PNG dimensions exceed local limits.')
            depth, color, compression, filtering, interlace = payload[8:]
            if (depth not in {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8),
                              4: (8, 16), 6: (8, 16)}.get(color, ())
                    or compression != 0 or filtering != 0 or interlace not in (0, 1)):
                raise ValueError('Unsupported PNG header.')
        elif kind == b'IHDR':
            raise ValueError('Duplicate PNG header.')
        image_data |= kind == b'IDAT'
        if kind == b'IEND':
            if size != 0 or end != len(data) or not image_data:
                raise ValueError('Invalid PNG ending.')
            return data
        position, chunks = end, chunks + 1
    raise ValueError('Incomplete PNG.')


def import_screenshot(paths, *, root=Path('artifacts/screenshots')):
    """Optional evidence failure never changes the actual assertion outcome."""
    if not isinstance(paths, tuple) or len(paths) != 1:
        return None
    try:
        directory = root.absolute()
        if directory.resolve(strict=True) != directory or directory.is_symlink():
            return None
        path = Path(paths[0])
        if '..' in path.parts or not re.fullmatch(r'[0-9a-f]{32}\.png', path.name):
            return None
        if path.parent.resolve(strict=True) != directory or path.is_symlink():
            return None
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_PNG_BYTES:
            return None
        if getattr(before, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
            return None
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size > MAX_PNG_BYTES
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                return None
            return validate_png(stream.read(MAX_PNG_BYTES + 1))
    except (OSError, ValueError, TypeError):
        return None
