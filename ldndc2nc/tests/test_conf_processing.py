import pytest

from ldndc2nc.ldndc2nc import _all_items_identical, _is_composite_var, _split_colname


def test_split_colname():
    assert _split_colname("dC_ch4_emis[kgCha-1]") == ("dC_ch4_emis", "kgCha-1")
    assert _split_colname("dC_ch4_emis") == ("dC_ch4_emis", "unknown")


@pytest.mark.parametrize(
    "input,result",
    [("dummy", False), (1.2, False), (("A", "B"), True), (["A", "B"], False)],
)
def test_is_composite_var_string(input, result):
    assert _is_composite_var(input) == result


@pytest.mark.parametrize("input,result", [([1, 1, 1], True), ([1, 1, 2], False)])
def test_all_items_identical(input, result):
    assert _all_items_identical(input) == result


def test_all_items_identical_empty():
    with pytest.raises(IndexError):
        _all_items_identical([])
