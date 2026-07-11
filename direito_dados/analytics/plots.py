"""Matplotlib/networkx visualizations of the norm-graph microsystem.

Every function lazily imports its plotting dependency and returns a
``matplotlib.figure.Figure`` without ever calling ``plt.show()``, so this
module is safe to use headlessly (tests, notebooks, batch report generation).
"""

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure


def plot_amendments_by_decade(by_decade: dict[int, int]) -> Figure:
    """Bar chart of amendment/revocation counts per decade."""
    import matplotlib.pyplot as plt

    decades = sorted(by_decade)
    counts = [by_decade[d] for d in decades]
    fig, ax = plt.subplots()
    ax.bar([str(d) for d in decades], counts, color="#2a6f97")
    ax.set_xlabel("Década")
    ax.set_ylabel("Nº de alterações/revogações")
    ax.set_title("Alterações do microssistema por década")
    fig.tight_layout()
    return fig


def plot_hierarchy_pyramid(distribution: dict[str, int]) -> Figure:
    """Horizontal bar chart of norm counts per hierarchy level."""
    import matplotlib.pyplot as plt

    levels = sorted(distribution, key=lambda k: distribution[k])
    counts = [distribution[level] for level in levels]
    fig, ax = plt.subplots()
    ax.barh(levels, counts, color="#a44a3f")
    ax.set_xlabel("Nº de normas")
    ax.set_ylabel("Nível hierárquico")
    ax.set_title("Distribuição das normas por nível hierárquico")
    fig.tight_layout()
    return fig


def plot_network(network_data: dict, max_nodes: int = 80) -> Figure:
    """Spring-layout graph of the (non-external) norm-graph subset."""
    import matplotlib.pyplot as plt
    import networkx as nx

    nodes = network_data["nodes"][:max_nodes]
    node_ids = {n["id"] for n in nodes}
    edges = [e for e in network_data["edges"] if e["src"] in node_ids and e["dst"] in node_ids]

    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n["id"], label=n["label"], kind=n["kind"])
    for e in edges:
        g.add_edge(e["src"], e["dst"], kind=e["kind"])

    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(g, seed=42)
    colors = ["#2a6f97" if g.nodes[n]["kind"] == "norm" else "#a44a3f" for n in g.nodes]
    nx.draw_networkx_nodes(g, pos, node_color=colors, node_size=200, ax=ax)
    nx.draw_networkx_edges(g, pos, arrows=True, alpha=0.5, ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=6, ax=ax)
    ax.set_title("Rede de normas e dispositivos")
    ax.axis("off")
    fig.tight_layout()
    return fig
