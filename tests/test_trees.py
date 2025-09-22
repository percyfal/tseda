import pytest

from tseda.vpages import trees


@pytest.fixture
def treespage(ds):
    return trees.TreesPage(datastore=ds)


@pytest.fixture
def tree(ds):
    return trees.Tree(datastore=ds)


def test_treespage(treespage):
    assert treespage.title == "Trees"
    assert treespage.key == "trees"


def test_tree(tree):
    assert ".node.n26 > .sym {fill: #e4ae38}" in tree.default_css or (
        ".node.n26 > .sym {fill: #e4ae38}; stroke: black; stroke-width: 2px;"
    )
