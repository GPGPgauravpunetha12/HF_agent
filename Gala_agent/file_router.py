# file_router.py
"""Dispatch downloaded files to the appropriate analysis tool.

The :func:`analyze_file` function inspects the file extension and invokes
the corresponding tool from ``tools.py``. Returns the tool's textual output
which can be appended to the agent prompt.
"""

from pathlib import Path

from tools import (
    pdf_reader_tool,
    excel_reader_tool,
    audio_transcriber_tool,
    image_info_tool,
    python_executor_tool,
)


def analyze_file(filepath: str) -> str:
    """Return the analysed content of *filepath*.

    Supported extensions:
    - ``.pdf``            → pdf_reader_tool
    - ``.xlsx`` / ``.xls`` → excel_reader_tool
    - ``.mp3`` / ``.wav``  → audio_transcriber_tool
    - image formats       → image_info_tool
    - ``.py``             → python_executor_tool
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        return pdf_reader_tool.invoke({"filepath": filepath})

    if ext in {".xlsx", ".xls"}:
        return excel_reader_tool.invoke({"filepath": filepath})

    if ext in {".mp3", ".wav", ".m4a"}:
        return audio_transcriber_tool.invoke({"filepath": filepath})

    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        # image_info_tool is decorated with @tool so call via .invoke()
        return image_info_tool.invoke({"filepath": filepath})

    if ext == ".py":
        return python_executor_tool.invoke({"filepath": filepath})

    return f"Unsupported file type: {ext} — file saved at {filepath}"
