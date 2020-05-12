import pytest

from ldndc2nc.variable import Variable, identical, valid_brackets, variables_compatible


def test_identical():
    assert identical(["A", "A", "A"]) is True
    assert identical(["A", "A", "B"]) is False
    assert identical([]) is True


test_data = [
    ("a", True),
    ("a[b]", True),
    ("a[]", True),
    ("a[b[c]]", False),
    ("a[[b]]", False),
    ("a[b][c]", False),
    ("a]b", False),
    ("a]b[", False),
    ("a[[b]", False),
]


@pytest.mark.parametrize("s,expected", test_data)
def test_valid_brackets(s, expected):
    assert valid_brackets(s) == expected


# test a bunch variable combinations
test_data = [
    ("n_emis", ["dN_n2o_emis[kgNha-1]", "dN_no_emis[kgNha-1]"], True),
    ("dN_emis", ["dN_n2o_emis[kgNha-1]", "dN_no_emis[kgNha-1]"], True),
    ("dC_emis", ["dN_n2o_emis[kgNha-1]", "dN_no_emis[kgNha-1]"], False),
    ("emission", ["dC_co2_emis[kgCha-1]", "dN_n2o_emis[kgNha-1]"], False),
    ("dN_n2o_emis[kgNha-1]", ["dN_n2o_emis[kgNha-1]"], True),
    ("aN_n2o_emis[kgNha-1]", ["dN_n2o_emis[kgNha-1]"], False),
    ("aN_emis", ["aN_n2o_emis[kgNha-1]", "aN_n2o_emis[kgNha-1]"], True),
    ("aN_emis", ["aN_n2o_emis[kgNha-1]", "aN_n2o_emis[kgNha-1]"], True),
    ("aC_emis", ["dC_co2_emis[kgCha-1]"], False),
    ("aN_n2o_emis[kgNha-1]", ["dN_n2o_emis[kgNha-1]", "dN_n2o_emis[kgNha-1]"], False),
]


@pytest.mark.parametrize("s,src,expected", test_data)
def test_variables_compatible(s, src, expected):
    assert variables_compatible(s, src) == expected


test_data = [
    ("dN_n2o_emis[kgNha-1]", ("dN_n2o_emis", "kgNha-1")),
    ("dN_n2o_emis", ("dN_n2o_emis", None)),
]


@pytest.mark.parametrize("s,expected", test_data)
def test_variable_decode(s, expected):
    assert Variable._decode(s) == expected


def test_variable_bad_decode():
    with pytest.raises(ValueError):
        Variable._decode("dN_n2o_emis[[kgNha-1]")


@pytest.mark.parametrize("expected,s", test_data)
def test_variable_encode(s, expected):
    assert Variable._encode(*s) == expected


test_data = [
    ("dN_n2o_emis[kgNha-1]", None, ["dN_n2o_emis[kgNha-1]"]),
    ("n_emis", "n2o_emis+no_emis", ["n2o_emis", "no_emis"]),
]


@pytest.mark.parametrize("s,sources,expected", test_data)
def test_variable_sources(s, sources, expected):
    v = Variable(s, sources=sources)
    assert v.sources == expected


test_data = [
    ("dN_n2o_emis[kgNha-1]", None, False),
    ("n2o", "dN_n2o_emis[kgNha-1]", False),
    ("n_emis", "n2o_emis+no_emis", True),
]


@pytest.mark.parametrize("s,sources,expected", test_data)
def test_variable_iscomposite(s, sources, expected):
    v = Variable(s, sources=sources)
    assert v.is_composite == expected


def test_variable_text():
    v = Variable("dN_n_emis[kgNha-1]=dN_n2o_emis[kgNha-1]+dN_no_emis[kgNha-1]")
    assert v.text == "dN_n_emis[kgNha-1]"


def test_variable_text_full():
    v = Variable("dN_n_emis[kgNha-1]=dN_n2o_emis[kgNha-1]+dN_no_emis[kgNha-1]")
    assert v.text_full == "dN_n_emis[kgNha-1]=dN_n2o_emis[kgNha-1]+dN_no_emis[kgNha-1]"
