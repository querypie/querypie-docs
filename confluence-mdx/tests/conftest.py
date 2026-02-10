"""pytest 공통 설정: bin/ 디렉터리를 sys.path에 추가."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
