import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session", autouse=True)
def isolated_appdata(tmp_path_factory):
    root = tmp_path_factory.mktemp("appdata")
    os.environ["APPDATA"] = str(root)
    return root


@pytest.fixture(scope="session")
def library(isolated_appdata):
    from visagecam.config import data_dir
    from visagecam.masks.library import MaskLibrary

    lib = MaskLibrary(data_dir() / "masks")
    lib.load()
    return lib
