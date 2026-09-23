# tests/run_all.py -- run every test module's _run_all() in one go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import (
    test_ailments,
    test_attributes,
    test_contagion,
    test_drift_check,
    test_engine,
    test_graph,
    test_guards,
    test_import_relationships,
    test_import_shopkeeper_customer,
    test_quarantine,
    test_religion,
    test_riot,
    test_romance,
    test_theft,
    test_violence,
)

MODULES = [
    test_graph,
    test_attributes,
    test_import_relationships,
    test_import_shopkeeper_customer,
    test_contagion,
    test_ailments,
    test_violence,
    test_romance,
    test_riot,
    test_guards,
    test_theft,
    test_religion,
    test_quarantine,
    test_drift_check,
    test_engine,
]

if __name__ == "__main__":
    for module in MODULES:
        print(f"{module.__name__}: ", end="")
        module._run_all()
    print("ALL OK")
