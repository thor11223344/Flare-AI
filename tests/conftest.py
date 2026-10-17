import os, tempfile
import pytest

# Use an isolated, smaller dataset so tests never touch the real data/ folder.
_tmp = tempfile.mkdtemp(prefix="wf_test_")
os.environ.update(WF_DATA_DIR=_tmp, N_TRACTS="800", POLICIES_PER_TRACT="100", SQLITE_PATH=os.path.join(_tmp, "t.db"))


@pytest.fixture(scope="session")
def pipeline():
    from src.data import generate
    from src.risk_model import train
    from src.audit import audit
    generate.run()
    m = train.train_and_score(save_plots=False)
    a = audit.run()
    return m, a
