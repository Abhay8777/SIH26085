from pydantic import BaseModel


class DrainageEdgeAnalysis(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    rainfall_runoff_m3s: float
    capacity_m3s: float
    utilization: float
    surcharge_m3s: float
    status: str


class DrainageAnalysis(BaseModel):
    source: str
    edges: list[DrainageEdgeAnalysis]