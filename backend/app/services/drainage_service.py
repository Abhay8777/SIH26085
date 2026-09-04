from backend.app.models.drainage import (
    DrainageEdge,
    DrainageNetwork,
    DrainageNode,
)


def generate_development_drainage_network() -> DrainageNetwork:
    """Generate a small synthetic drainage network.

    This is development/demo infrastructure data.
    It is NOT real Mumbai drainage infrastructure.
    """

    nodes = [
        DrainageNode(
            node_id="N1",
            latitude=19.0500,
            longitude=72.8500,
            elevation_m=12.0,
        ),
        DrainageNode(
            node_id="N2",
            latitude=19.0500,
            longitude=72.8590,
            elevation_m=11.5,
        ),
        DrainageNode(
            node_id="N3",
            latitude=19.0590,
            longitude=72.8590,
            elevation_m=9.0,
        ),
        DrainageNode(
            node_id="N4",
            latitude=19.0680,
            longitude=72.8590,
            elevation_m=8.0,
        ),
    ]

    edges = [
        DrainageEdge(
            edge_id="E1",
            from_node="N1",
            to_node="N2",
            length_m=1000.0,
            diameter_m=1.0,
            capacity_m3s=2.0,
        ),
        DrainageEdge(
            edge_id="E2",
            from_node="N2",
            to_node="N3",
            length_m=1000.0,
            diameter_m=0.8,
            capacity_m3s=1.2,
        ),
        DrainageEdge(
            edge_id="E3",
            from_node="N3",
            to_node="N4",
            length_m=1000.0,
            diameter_m=0.6,
            capacity_m3s=0.7,
        ),
    ]

    return DrainageNetwork(
        source="development_synthetic_network",
        nodes=nodes,
        edges=edges,
    )