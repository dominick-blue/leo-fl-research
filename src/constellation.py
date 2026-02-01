"""
Constellation Management Module

Managing collections of satellites for federated learning scheduling.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import numpy as np

from skyfield.api import load, wgs84, EarthSatellite
from .visibility_utils import compute_visibility_windows, compute_inter_satellite_visibility


@dataclass
class SatelliteNode:
    """Represents a satellite as a federated learning node."""
    satellite: EarthSatellite
    node_id: str
    orbital_plane: int = 0
    position_in_plane: int = 0
    compute_capacity: float = 1.0  # Relative compute capacity
    model_version: int = 0

    @property
    def name(self) -> str:
        return self.satellite.name


class Constellation:
    """
    Manages a constellation of satellites for FL scheduling.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: Dict[str, SatelliteNode] = {}
        self.ts = load.timescale()

    def add_from_tle_file(self, filepath: str) -> int:
        """
        Add satellites from a TLE file.

        Returns:
            Number of satellites added
        """
        satellites = load.tle_file(filepath)
        count = 0
        for sat in satellites:
            node_id = f"sat_{len(self.nodes)}"
            self.nodes[node_id] = SatelliteNode(
                satellite=sat,
                node_id=node_id,
            )
            count += 1
        return count

    def add_satellite(self, satellite: EarthSatellite, **kwargs) -> str:
        """
        Add a single satellite to the constellation.

        Returns:
            Node ID of added satellite
        """
        node_id = f"sat_{len(self.nodes)}"
        self.nodes[node_id] = SatelliteNode(
            satellite=satellite,
            node_id=node_id,
            **kwargs,
        )
        return node_id

    def get_visible_nodes(
        self,
        ground_station,
        time,
        min_elevation: float = 10.0,
    ) -> List[SatelliteNode]:
        """
        Get all nodes visible from a ground station at a given time.
        """
        visible = []
        for node in self.nodes.values():
            diff = node.satellite - ground_station
            topo = diff.at(time)
            alt, _, _ = topo.altaz()
            if alt.degrees >= min_elevation:
                visible.append(node)
        return visible

    def get_communication_graph(
        self,
        time,
        max_range_km: float = 5000.0,
    ) -> Dict[str, Set[str]]:
        """
        Build inter-satellite communication graph at a given time.

        Returns:
            Adjacency dict: node_id -> set of reachable node_ids
        """
        graph = {node_id: set() for node_id in self.nodes}

        node_list = list(self.nodes.values())
        for i, node1 in enumerate(node_list):
            for node2 in node_list[i+1:]:
                can_comm, _ = compute_inter_satellite_visibility(
                    node1.satellite,
                    node2.satellite,
                    time,
                    max_range_km,
                )
                if can_comm:
                    graph[node1.node_id].add(node2.node_id)
                    graph[node2.node_id].add(node1.node_id)

        return graph

    def schedule_aggregation_window(
        self,
        ground_station,
        start_time,
        duration_hours: float = 24.0,
        min_visible_nodes: int = 3,
    ) -> List[dict]:
        """
        Find time windows suitable for model aggregation.

        Args:
            ground_station: Aggregator ground station
            start_time: Start of search window
            duration_hours: Search duration in hours
            min_visible_nodes: Minimum satellites needed for aggregation

        Returns:
            List of aggregation opportunities
        """
        end_time = self.ts.tt_jd(start_time.tt + duration_hours / 24.0)
        opportunities = []

        # Sample at 1-minute intervals
        num_samples = int(duration_hours * 60)
        times = self.ts.tt_jd(np.linspace(
            start_time.tt,
            end_time.tt,
            num_samples,
        ))

        for t in times:
            visible = self.get_visible_nodes(ground_station, t)
            if len(visible) >= min_visible_nodes:
                opportunities.append({
                    'time': t,
                    'visible_count': len(visible),
                    'nodes': [n.node_id for n in visible],
                })

        return opportunities

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"Constellation(name='{self.name}', satellites={len(self.nodes)})"
