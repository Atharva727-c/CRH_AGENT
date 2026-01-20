from __future__ import annotations

import os
from datetime import datetime


def save_ppt_text(*, base_name: str, text: str, out_dir: str = "ppt_outputs") -> str:
    """
    Save generated PPT narrative to a timestamped .txt file.
    Returns the written file path.
    """
    os.makedirs(out_dir, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base_name)[:80]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"{safe}_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text or "")
        f.write("\n")
    return path


