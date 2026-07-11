import pytest

pytest.importorskip("matplotlib")

from direito_dados.analytics.plots import plot_amendments_by_decade, plot_hierarchy_pyramid

def test_decade_plot_returns_figure():
    import matplotlib
    fig = plot_amendments_by_decade({1980: 3, 2010: 5})
    assert isinstance(fig, matplotlib.figure.Figure)

def test_hierarchy_plot_returns_figure():
    import matplotlib
    fig = plot_hierarchy_pyramid({"CONSTITUICAO": 1, "DECRETO_LEI": 3})
    assert isinstance(fig, matplotlib.figure.Figure)

def test_network_plot_guarded_by_networkx():
    pytest.importorskip("networkx")
    import matplotlib
    from direito_dados.analytics.plots import plot_network
    data = {"nodes": [{"id": "CP", "kind": "norm", "label": "CP", "domain": "penal", "status": None}],
            "edges": []}
    assert isinstance(plot_network(data), matplotlib.figure.Figure)
