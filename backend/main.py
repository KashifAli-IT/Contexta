"""uvicorn entrypoint: `python main.py` or `uvicorn main:app`.

`app.main:app` is the canonical target; this file exists so the image can be
run with a plain `python main.py` during debugging.
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "0") == "1",
    )
