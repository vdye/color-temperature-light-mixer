"""Utility functions and classes for computing the light brightness and temperature."""

from dataclasses import dataclass
from enum import StrEnum, auto
import logging
import math

from homeassistant.util.color import (
    color_temperature_kelvin_to_mired,
    rgbww_to_color_temperature,
    color_temperature_to_rgbww,
)

_LOGGER = logging.getLogger(__name__)
BRIGHTNESS_RANGE = (1, 255)


class BrightnessTemperaturePriority(StrEnum):
    """Enum that indicates what to prefer in the computation of the target brightness required to (temperature, brightness) target tuple."""

    BRIGHTNESS = auto()
    """Maintain the target brightness, at the expense of the temperature"""
    TEMPERATURE = auto()
    """Maintain the target temperature, at the expense of the brightness"""
    MIXED = auto()
    """Try to target a mix of both temperature and brightness"""


@dataclass
class TurnOnSettings:
    """Options to pass to the light to be turned on."""

    entity_id: str
    common_data: dict[str, int]
    brightness: int | None = None


@dataclass
class TemperatureCalculator:
    """Class for computing the temperature of two combined lights of different temperature, depending on their brightness level."""

    warm_brightness: int
    """Brightness of the warm light in the range 1...255"""
    warm_temperature_kelvin: int
    """Temperature of the warm light in kelvin"""
    cold_brightness: int
    """Brightness of the cold light in the range 1...255"""
    cold_temperature_kelvin: int
    """Temperature of the cold light in kelvin"""

    def current_temperature(self) -> int:
        """Compute the current combined temperature."""

        combined_temperature, _ = rgbww_to_color_temperature(
            (0, 0, 0, self.cold_brightness, self.warm_brightness),
            self.warm_temperature_kelvin,
            self.cold_temperature_kelvin,
        )

        # Clamp the computed temperature between the min and maximum supported temperatures
        return max(
            self.warm_temperature_kelvin,
            min(self.cold_temperature_kelvin, combined_temperature),
        )


@dataclass
class BrightnessCalculator:
    """Class that given a target temperature and target, computes the brightness of the two combined lights."""

    warm_temperature_kelvin: int
    """Temperature of the warm light in kelvin"""
    cold_temperature_kelvin: int
    """Temperature of the cold light in kelvin"""

    target_temperature_kelvin: int
    """Target temperature in kelvin to reach"""
    target_brightness: int
    """Target brightness to reach in the range 1...255"""

    priority: BrightnessTemperaturePriority = BrightnessTemperaturePriority.MIXED
    """Govern the behavior when we we want to reach a brightness and temperature outside the admissable range"""

    def compute_brightnesses(self) -> tuple[int, int]:
        """Compute the warm and cold light brightness required to reach the target temperature.

        Returns:
            (warm, cold) brightness in range 1-255

        """

        _LOGGER.debug(
            "Computing brightness for temp: %d, bright: %d, priority: %s",
            self.target_temperature_kelvin,
            self.target_brightness,
            self.priority.name,
        )

        # Get target cold/warm brightnesses
        #
        # Option 1: keep a constant brightness throughout the temperature range,
        # attenuating the mid-ranges down to match the extremes.
        _, _, _, cold_brightness, warm_brightness = color_temperature_to_rgbww(
            self.target_temperature_kelvin,
            self.target_brightness,
            self.warm_temperature_kelvin,
            self.cold_temperature_kelvin,
        )

        # TODO Option 2: use the maximum available brightness as the baseline of
        # 100% for a given color temperature.

        # Clamp brightness to acceptable ranges
        warm_brightness = min(warm_brightness, BRIGHTNESS_RANGE[1])
        cold_brightness = min(cold_brightness, BRIGHTNESS_RANGE[1])
        return round(warm_brightness), round(cold_brightness)
