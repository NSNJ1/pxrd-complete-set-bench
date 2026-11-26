"""Small, retrying ZIP-member reader based on HTTP byte ranges."""

from __future__ import annotations

import binascii
import struct
import time
import zipfile
import zlib

import requests
from remotezip import RemoteZip

USER_AGENT = "precursor-genome-benchmark/1.0"


def _request_range(
    url: str,
    start: int,
    end: int,
    attempts: int = 8,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                headers={
                    "Range": f"bytes={start}-{end}",
                    "Accept-Encoding": "identity",
                    "User-Agent": USER_AGENT,
                },
                timeout=(30, 240),
            )
            response.raise_for_status()
            expected = end - start + 1
            if response.status_code != 206:
                raise RuntimeError(
                    f"range request returned HTTP {response.status_code}"
                )
            if len(response.content) != expected:
                raise RuntimeError(
                    f"range request returned {len(response.content)} bytes; "
                    f"expected {expected}"
                )
            return response.content
        except Exception as error:  # noqa: BLE001 - retry all transport errors
            last_error = error
            time.sleep(min(2 + attempt * 2, 12))
    raise RuntimeError(f"range request failed for {url}: {last_error}")


def read_member(url: str, member: str, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with RemoteZip(url) as archive:
                info = archive.getinfo(member)
            local_header = _request_range(
                url,
                info.header_offset,
                info.header_offset + 29,
            )
            (
                signature,
                _version,
                _flags,
                method,
                _mtime,
                _mdate,
                _crc,
                _compressed_size,
                _file_size,
                name_length,
                extra_length,
            ) = struct.unpack("<4sHHHHHIIIHH", local_header)
            if signature != b"PK\x03\x04":
                raise ValueError("invalid local ZIP header")
            data_offset = info.header_offset + 30 + name_length + extra_length
            compressed = _request_range(
                url,
                data_offset,
                data_offset + info.compress_size - 1,
            )
            if method == zipfile.ZIP_STORED:
                payload = compressed
            elif method == zipfile.ZIP_DEFLATED:
                payload = zlib.decompress(compressed, -zlib.MAX_WBITS)
            else:
                raise ValueError(f"unsupported ZIP method: {method}")
            if len(payload) != info.file_size:
                raise ValueError(
                    f"member size mismatch: {len(payload)} != {info.file_size}"
                )
            if binascii.crc32(payload) & 0xFFFFFFFF != info.CRC:
                raise ValueError("ZIP member CRC mismatch")
            return payload
        except Exception as error:  # noqa: BLE001 - retry ZIP/network failures
            last_error = error
            time.sleep(2)
    raise RuntimeError(f"failed to read {member}: {last_error}")
