"""Gate V5b (second published-spectrum reproduction, AREA mode) structure tests.

Asserts the recomputed ``gates.V5b`` entry exists with the expected shape and
the pre-registered +/-10% window, WITHOUT asserting a specific measured number
(only that it is finite). Also asserts the existing ``gates.V5`` entry is still
present and unchanged in shape.
"""

import math

from ramanuq.reporting import compute_report_data


def _gates():
    return compute_report_data()["gates"]


def test_v5b_present_and_well_formed():
    gates = _gates()
    assert "V5b" in gates
    v5b = gates["V5b"]

    measured = v5b["measured_idig"]
    assert isinstance(measured, (int, float)) and math.isfinite(float(measured))

    assert v5b["window"] == [1.476, 1.804]
    assert v5b["result"] in {"PASS", "MISS"}
    assert v5b["intensity_mode"] == "area"


def test_v5_still_present_and_unchanged_in_shape():
    gates = _gates()
    assert "V5" in gates
    v5 = gates["V5"]

    # V5 keeps its HEIGHT-mode identity and the same result-dict shape.
    assert v5["intensity_mode"] == "height"
    assert v5["spectrum"] == "cancado2011_v5"
    assert v5["result"] in {"PASS", "MISS"}
    assert set(gates["V5b"].keys()) == set(v5.keys())
