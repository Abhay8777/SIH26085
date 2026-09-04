from pydantic import BaseModel


class DrainageNode(BaseModel):
    """A stormwater drainage node such as a manhole or inlet."""

    node_id: str
    latitude: float
    longitude: float
    elevation_m: float


class DrainageEdge(BaseModel):
    """A directed connection between two drainage nodes."""

    edge_id: str
    from_node: str
    to_node: str
    length_m: float
    diameter_m: float
    capacity_m3s: float


class DrainageNetwork(BaseModel):
    """Directed urban stormwater drainage network."""

    source: str
    nodes: list[DrainageNode]
    edges: list[DrainageEdge]