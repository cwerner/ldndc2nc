import pytest

from ldndc2nc.ldndc2nc import _split_colname, _is_composite_var, _all_items_identical


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


@pytest.mark.xfail(raises=IndexError)
def test_all_items_identical_empty():
    _all_items_identical([])
