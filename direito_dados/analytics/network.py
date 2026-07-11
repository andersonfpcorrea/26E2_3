"""Serializable node/edge export of the norm-graph for visualization."""

from direito_dados.graph.models import NormGraph


def to_network_data(graph: NormGraph, include_external: bool = False) -> dict:
    excluded: set[str] = set()
    nodes = []
    for node in graph.nodes.values():
        if not include_external and node.attrs.get("external"):
            excluded.add(node.id)
            continue
        nodes.append({
            "id": node.id,
            "kind": node.kind.value,
            "label": node.label,
            "domain": node.domain,
            "status": node.attrs.get("status"),
        })
    edges = []
    for e in graph.edges:
        if e.src in excluded or e.dst in excluded:
            continue
        edges.append({"src": e.src, "dst": e.dst, "kind": e.kind.value,
                      "year": e.attrs.get("year")})
    return {"nodes": nodes, "edges": edges}
