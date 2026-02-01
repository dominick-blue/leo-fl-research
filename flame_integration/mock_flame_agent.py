"""
Mock FLAME Agent Module

Simulates federated learning agent behavior for LEO satellite nodes.
This is a placeholder for integration with actual FL frameworks.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np
from enum import Enum


class AgentState(Enum):
    """Possible states for a FL agent."""
    IDLE = "idle"
    TRAINING = "training"
    UPLOADING = "uploading"
    DOWNLOADING = "downloading"
    WAITING = "waiting"


@dataclass
class ModelUpdate:
    """Represents a model update from a satellite node."""
    node_id: str
    round_number: int
    weights: Dict[str, np.ndarray] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    samples_trained: int = 0
    timestamp: float = 0.0


class MockFlameAgent:
    """
    Simulates a federated learning agent running on a satellite.

    This mock agent demonstrates the "swap" concept where model
    updates are exchanged during visibility windows.
    """

    def __init__(
        self,
        node_id: str,
        model_size_mb: float = 100.0,
        compute_speed: float = 1.0,
    ):
        self.node_id = node_id
        self.model_size_mb = model_size_mb
        self.compute_speed = compute_speed

        self.state = AgentState.IDLE
        self.current_round = 0
        self.local_model: Dict[str, np.ndarray] = {}
        self.pending_updates: List[ModelUpdate] = []

    def initialize_model(self, global_weights: Dict[str, np.ndarray]):
        """Initialize local model with global weights."""
        self.local_model = {k: v.copy() for k, v in global_weights.items()}
        self.state = AgentState.IDLE

    def train_local(
        self,
        data_samples: int,
        epochs: int = 1,
    ) -> ModelUpdate:
        """
        Simulate local training.

        Args:
            data_samples: Number of local data samples
            epochs: Number of local epochs

        Returns:
            ModelUpdate with simulated weight updates
        """
        self.state = AgentState.TRAINING

        # Simulate training by adding noise to weights
        updated_weights = {}
        for name, weight in self.local_model.items():
            # Simulate gradient update with random noise
            gradient = np.random.randn(*weight.shape) * 0.01
            updated_weights[name] = weight - gradient

        self.local_model = updated_weights
        self.current_round += 1

        update = ModelUpdate(
            node_id=self.node_id,
            round_number=self.current_round,
            weights=updated_weights,
            metrics={
                "loss": np.random.uniform(0.1, 1.0),
                "accuracy": np.random.uniform(0.7, 0.95),
            },
            samples_trained=data_samples * epochs,
        )

        self.state = AgentState.IDLE
        return update

    def prepare_upload(self) -> ModelUpdate:
        """Prepare model update for upload during visibility window."""
        self.state = AgentState.UPLOADING

        update = ModelUpdate(
            node_id=self.node_id,
            round_number=self.current_round,
            weights=self.local_model,
            samples_trained=0,
        )

        return update

    def receive_global_model(self, global_weights: Dict[str, np.ndarray]):
        """Receive and apply global model from aggregator."""
        self.state = AgentState.DOWNLOADING
        self.local_model = {k: v.copy() for k, v in global_weights.items()}
        self.state = AgentState.IDLE

    def estimate_transfer_time(
        self,
        bandwidth_mbps: float,
        elevation_deg: float,
    ) -> float:
        """
        Estimate time to transfer model given link conditions.

        Args:
            bandwidth_mbps: Available bandwidth in Mbps
            elevation_deg: Elevation angle (affects link quality)

        Returns:
            Estimated transfer time in seconds
        """
        # Simple model: bandwidth degrades at low elevations
        effective_bandwidth = bandwidth_mbps * min(1.0, elevation_deg / 30.0)
        transfer_time = (self.model_size_mb * 8) / effective_bandwidth
        return transfer_time

    def can_complete_exchange(
        self,
        window_duration_sec: float,
        bandwidth_mbps: float,
        elevation_deg: float,
    ) -> bool:
        """
        Check if model exchange can complete in visibility window.

        Args:
            window_duration_sec: Duration of visibility window
            bandwidth_mbps: Available bandwidth
            elevation_deg: Elevation angle

        Returns:
            True if exchange can complete
        """
        transfer_time = self.estimate_transfer_time(bandwidth_mbps, elevation_deg)
        # Need time for both upload and download
        total_time = transfer_time * 2
        return total_time < window_duration_sec

    def __repr__(self) -> str:
        return f"MockFlameAgent(node_id='{self.node_id}', state={self.state.value}, round={self.current_round})"


class MockAggregator:
    """
    Simulates a federated learning aggregator (ground station or lead satellite).
    """

    def __init__(self, aggregator_id: str = "ground_0"):
        self.aggregator_id = aggregator_id
        self.global_model: Dict[str, np.ndarray] = {}
        self.received_updates: List[ModelUpdate] = []
        self.current_round = 0

    def initialize_global_model(self, model_spec: Dict[str, tuple]):
        """
        Initialize global model with given layer specifications.

        Args:
            model_spec: Dict of layer_name -> shape tuple
        """
        self.global_model = {
            name: np.random.randn(*shape) * 0.1
            for name, shape in model_spec.items()
        }

    def receive_update(self, update: ModelUpdate):
        """Receive model update from a satellite node."""
        self.received_updates.append(update)

    def aggregate(self, min_updates: int = 2) -> bool:
        """
        Perform FedAvg aggregation on received updates.

        Args:
            min_updates: Minimum updates required for aggregation

        Returns:
            True if aggregation was performed
        """
        if len(self.received_updates) < min_updates:
            return False

        # FedAvg: weighted average by samples trained
        total_samples = sum(u.samples_trained for u in self.received_updates)
        if total_samples == 0:
            total_samples = len(self.received_updates)

        new_weights = {}
        for layer_name in self.global_model.keys():
            weighted_sum = np.zeros_like(self.global_model[layer_name])
            for update in self.received_updates:
                weight = update.samples_trained / total_samples if total_samples > 0 else 1.0 / len(self.received_updates)
                weighted_sum += update.weights.get(layer_name, self.global_model[layer_name]) * weight
            new_weights[layer_name] = weighted_sum

        self.global_model = new_weights
        self.current_round += 1
        self.received_updates = []

        return True

    def get_global_model(self) -> Dict[str, np.ndarray]:
        """Get current global model weights."""
        return {k: v.copy() for k, v in self.global_model.items()}

    def __repr__(self) -> str:
        return f"MockAggregator(id='{self.aggregator_id}', round={self.current_round}, pending_updates={len(self.received_updates)})"
