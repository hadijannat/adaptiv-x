"""
FMU Runner for Adaptiv-Monitor.

Downloads and runs FMU (Functional Mock-up Unit) simulations using FMPy.
Provides physics-based expected values for comparison with actual measurements.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import numpy as np
from fmpy import simulate_fmu
from fmpy.util import download_file

if TYPE_CHECKING:
    from adaptiv_monitor.basyx_client import BasyxClient

logger = logging.getLogger(__name__)


class FMURunner:
    """Runs FMU simulations for physics-based validation."""

    def __init__(
        self,
        minio_endpoint: str = "localhost:9000",
        minio_access_key: str = "adaptivx",
        minio_secret_key: str = "adaptivx123",
        minio_bucket: str = "adaptivx-fmu",
        cache_dir: str | None = None,
    ) -> None:
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.minio_bucket = minio_bucket
        self._cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "fmu_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._fmu_cache: dict[str, Path] = {}

    async def simulate(
        self,
        asset_id: str,
        omega: float,
        load: float,
        wear: float,
        basyx_client: BasyxClient,
    ) -> dict[str, float]:
        """
        Run FMU simulation and return expected values.

        Args:
            asset_id: Asset identifier to get FMU reference from AAS
            omega: Spindle speed [rad/s]
            load: Cutting load [N]
            wear: Wear level [0-1]
            basyx_client: BaSyx client for AAS access

        Returns:
            Dictionary with simulation outputs
        """
        # Get FMU path (from cache or download)
        fmu_path = await self._get_fmu(asset_id, basyx_client)
        if not fmu_path:
            logger.warning(f"No FMU available for {asset_id}, using fallback calculation")
            return self._fallback_calculation(omega, load, wear)

        # Run simulation
        try:
            result = simulate_fmu(
                str(fmu_path),
                start_values={
                    "omega": omega,
                    "load": load,
                    "wear": wear,
                },
                output=["vib_rms_expected", "power_loss_expected", "temperature_rise_expected"],
                stop_time=0.1,  # Short simulation for steady-state
            )

            # Extract final values
            return {
                "vib_rms_expected": float(result["vib_rms_expected"][-1]),
                "power_loss_expected": float(result["power_loss_expected"][-1]),
                "temperature_rise_expected": float(result["temperature_rise_expected"][-1]),
            }

        except Exception as e:
            logger.error(f"FMU simulation failed: {e}")
            return self._fallback_calculation(omega, load, wear)

    async def _get_fmu(
        self, asset_id: str, basyx_client: BasyxClient
    ) -> Path | None:
        """Get FMU file path, downloading if necessary."""
        # Check cache
        if asset_id in self._fmu_cache:
            cached = self._fmu_cache[asset_id]
            if cached.exists():
                return cached

        # Get FMU URL from AAS
        fmu_url = await basyx_client.get_fmu_url(asset_id)
        if not fmu_url:
            logger.warning(f"No FMU URL found for {asset_id}")
            # Try default location
            fmu_url = f"http://{self.minio_endpoint}/{self.minio_bucket}/bearing_wear.fmu"

        # Download FMU
        try:
            fmu_path = self._cache_dir / f"{asset_id}_bearing_wear.fmu"

            async with httpx.AsyncClient() as client:
                response = await client.get(fmu_url, timeout=30.0)
                response.raise_for_status()
                fmu_path.write_bytes(response.content)

            self._fmu_cache[asset_id] = fmu_path
            logger.info(f"Downloaded FMU for {asset_id} to {fmu_path}")
            return fmu_path

        except Exception as e:
            logger.error(f"Failed to download FMU from {fmu_url}: {e}")
            return None

    def _fallback_calculation(
        self, omega: float, load: float, wear: float
    ) -> dict[str, float]:
        """
        Fallback physics calculation when FMU is unavailable.

        Uses the same model equations as BearingWear.mo
        """
        # Vibration model coefficients
        vib_base = 0.5
        k1, k2, k3, k4 = 0.001, 0.002, 3.0, 0.005

        # Power loss coefficients
        power_base = 50.0
        c1, c2 = 0.0001, 0.5

        # Thermal resistance
        thermal_resistance = 0.02

        # Calculate outputs
        vib_rms_expected = vib_base + k1 * omega + k2 * load + k3 * wear + k4 * wear * omega
        power_loss_expected = power_base + c1 * load * omega + c2 * wear * load
        temperature_rise_expected = thermal_resistance * power_loss_expected

        return {
            "vib_rms_expected": vib_rms_expected,
            "power_loss_expected": power_loss_expected,
            "temperature_rise_expected": temperature_rise_expected,
        }

    def clear_cache(self) -> None:
        """Clear the FMU cache."""
        self._fmu_cache.clear()
        for fmu_file in self._cache_dir.glob("*.fmu"):
            fmu_file.unlink()
