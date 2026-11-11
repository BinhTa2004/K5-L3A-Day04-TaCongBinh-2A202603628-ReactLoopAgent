"""Nạp cấu hình .env bằng standard library, không thực thi lệnh shell."""
import os
from pathlib import Path


def load_env(path=None):
    """Đọc KEY=value; biến đã đặt trong terminal được ưu tiên."""
    env_path = Path(path) if path is not None else Path(__file__).resolve().parent / '.env'
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        name, separator, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if not separator or not name.isidentifier() or not name.isascii():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ.setdefault(name, value)
