"""
K-Nearest Neighbors implementation for weather event analysis.
Finds similar historical weather events based on numerical features.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherKNN:
    """
    K-Nearest Neighbors for weather event similarity analysis.
    Uses Euclidean distance on normalized weather features.
    """

    def __init__(self, k: int = 5):
        """
        Initialize KNN analyzer.

        Args:
            k: Number of nearest neighbors to find
        """
        self.k = k
        self.feature_columns = [
            'temperature_c',
            'wind_speed_kmh',
            'precipitation_mm',
            'humidity_percent',
            'duration_hours'
        ]
        self.historical_events = None
        self.normalized_features = None
        self.feature_stats = {}

    def load_historical_data(self, events_df: pd.DataFrame):
        """
        Load and normalize historical weather event data.

        Args:
            events_df: DataFrame with historical weather events
        """
        self.historical_events = events_df.copy()

        # Calculate statistics for normalization
        for col in self.feature_columns:
            self.feature_stats[col] = {
                'mean': events_df[col].mean(),
                'std': events_df[col].std()
            }

        # Normalize features (z-score normalization)
        self.normalized_features = self._normalize_features(
            events_df[self.feature_columns]
        )

        logger.info(f"Loaded {len(events_df)} historical weather events")

    def _normalize_features(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Normalize features using z-score normalization.

        Args:
            features_df: DataFrame with feature columns

        Returns:
            Normalized feature array
        """
        normalized = np.zeros(features_df.shape)

        for i, col in enumerate(self.feature_columns):
            mean = self.feature_stats[col]['mean']
            std = self.feature_stats[col]['std']
            if std > 0:
                normalized[:, i] = (features_df[col] - mean) / std
            else:
                normalized[:, i] = 0

        return normalized

    def _euclidean_distance(self, point1: np.ndarray, point2: np.ndarray) -> float:
        """
        Calculate Euclidean distance between two points.

        Args:
            point1: First point
            point2: Second point

        Returns:
            Euclidean distance
        """
        return np.sqrt(np.sum((point1 - point2) ** 2))

    def find_similar_events(self, current_event: Dict) -> List[Tuple[int, float]]:
        """
        Find k most similar historical weather events.

        Args:
            current_event: Dictionary with current weather event features

        Returns:
            List of tuples (event_id, distance) for k nearest neighbors
        """
        # Extract and normalize current event features
        current_features = np.array([
            current_event[col] for col in self.feature_columns
        ]).reshape(1, -1)

        # Normalize current event using historical statistics
        normalized_current = np.zeros(current_features.shape)
        for i, col in enumerate(self.feature_columns):
            mean = self.feature_stats[col]['mean']
            std = self.feature_stats[col]['std']
            if std > 0:
                normalized_current[0, i] = (current_features[0, i] - mean) / std
            else:
                normalized_current[0, i] = 0

        # Calculate distances to all historical events
        distances = []
        for idx in range(len(self.normalized_features)):
            dist = self._euclidean_distance(
                normalized_current[0],
                self.normalized_features[idx]
            )
            event_id = self.historical_events.iloc[idx]['event_id']
            distances.append((event_id, dist))

        # Sort by distance and return k nearest
        distances.sort(key=lambda x: x[1])
        return distances[:self.k]

    def get_event_details(self, event_id: int) -> Dict:
        """
        Get details of a specific historical event.

        Args:
            event_id: ID of the event

        Returns:
            Dictionary with event details
        """
        event = self.historical_events[
            self.historical_events['event_id'] == event_id
        ].iloc[0]
        return event.to_dict()


class AssetImpactAnalyzer:
    """
    Analyzes which assets were affected in similar historical weather events.
    """

    def __init__(self, assets_df: pd.DataFrame, incidents_df: pd.DataFrame):
        """
        Initialize asset impact analyzer.

        Args:
            assets_df: DataFrame with asset information
            incidents_df: DataFrame with historical incidents
        """
        self.assets = assets_df
        self.incidents = incidents_df
        logger.info(f"Loaded {len(assets_df)} assets and {len(incidents_df)} incidents")

    def get_affected_assets(self, event_ids: List[int]) -> pd.DataFrame:
        """
        Get all assets affected in the given weather events.

        Args:
            event_ids: List of weather event IDs

        Returns:
            DataFrame with affected assets and incident details
        """
        # Filter incidents for these events
        affected_incidents = self.incidents[
            self.incidents['event_id'].isin(event_ids)
        ]

        # Join with asset information
        affected_assets = affected_incidents.merge(
            self.assets,
            left_on='asset_code',
            right_on='code',
            how='left'
        )

        return affected_assets

    def analyze_risk_patterns(self, affected_assets: pd.DataFrame) -> Dict:
        """
        Analyze patterns in affected assets to identify risk factors.

        Args:
            affected_assets: DataFrame with affected assets

        Returns:
            Dictionary with risk analysis
        """
        if len(affected_assets) == 0:
            return {
                'total_incidents': 0,
                'unique_assets': 0,
                'by_asset_type': {},
                'by_criticality': {},
                'by_damage_severity': {},
                'high_risk_assets': []
            }

        # Count incidents by various dimensions
        by_asset_type = affected_assets.groupby('type').size().to_dict()
        by_criticality = affected_assets.groupby('criticality').size().to_dict()
        by_severity = affected_assets.groupby('damage_severity').size().to_dict()

        # Identify frequently affected assets
        asset_frequency = affected_assets.groupby('code').size()
        high_risk_assets = asset_frequency.sort_values(ascending=False).head(10)

        high_risk_list = []
        for asset_code, count in high_risk_assets.items():
            asset_info = self.assets[self.assets['code'] == asset_code].iloc[0]
            high_risk_list.append({
                'code': asset_code,
                'name': asset_info['name'],
                'type': asset_info['type'],
                'incident_count': int(count),
                'criticality': asset_info['criticality']
            })

        return {
            'total_incidents': len(affected_assets),
            'unique_assets': affected_assets['code'].nunique(),
            'by_asset_type': by_asset_type,
            'by_criticality': by_criticality,
            'by_damage_severity': by_severity,
            'high_risk_assets': high_risk_list,
            'total_estimated_cost': float(affected_assets['repair_cost_usd'].sum()),
            'total_downtime_hours': float(affected_assets['downtime_hours'].sum())
        }

    def predict_at_risk_assets(self, risk_analysis: Dict) -> List[Dict]:
        """
        Predict which current assets are at risk based on historical patterns.

        Args:
            risk_analysis: Risk analysis from analyze_risk_patterns

        Returns:
            List of assets predicted to be at risk
        """
        at_risk = []

        # Get high-risk asset types from historical data
        risk_asset_types = risk_analysis.get('by_asset_type', {})

        for asset_type, incident_count in risk_asset_types.items():
            # Find all current assets of this type
            matching_assets = self.assets[self.assets['type'] == asset_type]

            for _, asset in matching_assets.iterrows():
                # Calculate risk score based on:
                # - Historical incident count for this asset type
                # - Asset age
                # - Asset condition
                # - Asset criticality

                # Calculate age from installation_date
                installation_date = pd.to_datetime(asset['installation_date'])
                current_date = datetime.now()
                age_years = (current_date - installation_date).days / 365.25

                criticality_weight = {
                    'Critical': 1.5,
                    'High': 1.2,
                    'Medium': 1.0,
                    'Low': 0.8
                }.get(asset['criticality'], 1.0)

                # Lower condition score = higher risk
                condition_risk = (10 - asset['condition_score']) / 10

                # Older assets are higher risk
                age_risk = min(age_years / 30, 1.0)

                risk_score = (
                    incident_count * 0.4 +
                    condition_risk * 30 * 0.3 +
                    age_risk * 30 * 0.2 +
                    criticality_weight * 10 * 0.1
                )

                at_risk.append({
                    'code': asset['code'],
                    'name': asset['name'],
                    'type': asset['type'],
                    'category': asset['category'],
                    'risk_score': round(risk_score, 2),
                    'criticality': asset['criticality'],
                    'condition_score': asset['condition_score'],
                    'age_years': round(age_years, 1),
                    'installation_date': asset['installation_date'],
                    'historical_incident_count': incident_count
                })

        # Sort by risk score
        at_risk.sort(key=lambda x: x['risk_score'], reverse=True)

        return at_risk

