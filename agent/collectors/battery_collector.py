"""
Battery & Power Collector for InfraMind AI Windows Agent
"""

import psutil
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import BatteryMetrics


class BatteryCollector(BaseCollector):
    """Collector for Battery status and power metrics using psutil."""

    def __init__(self):
        super().__init__(name="battery")

    def collect(self) -> BatteryMetrics:
        """
        Collects real battery status and AC power connectivity.
        
        :return: BatteryMetrics Pydantic instance.
        """
        try:
            self.logger.debug("Collecting Battery metrics...")
            battery = psutil.sensors_battery()

            if battery is None:
                # System is a desktop PC or has no battery sensor
                return BatteryMetrics(
                    has_battery=False,
                    percentage=None,
                    power_plugged=True,  # Desktops are directly plugged into wall power
                    seconds_left=None,
                    formatted_time_left=None
                )

            percentage = round(battery.percent, 2)
            power_plugged = battery.power_plugged
            seconds_left = battery.secsleft if battery.secsleft not in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED) else None
            
            formatted_time_left = None
            if seconds_left is not None and seconds_left > 0:
                hours, remainder = divmod(seconds_left, 3600)
                minutes, _ = divmod(remainder, 60)
                formatted_time_left = f"{hours}h {minutes}m"
            elif power_plugged:
                formatted_time_left = "AC Power Connected (Charging/Full)"

            return BatteryMetrics(
                has_battery=True,
                percentage=percentage,
                power_plugged=power_plugged,
                seconds_left=seconds_left,
                formatted_time_left=formatted_time_left
            )

        except Exception as e:
            self.logger.error(f"Error collecting Battery metrics: {e}", exc_info=True)
            return BatteryMetrics(
                has_battery=False,
                percentage=None,
                power_plugged=None,
                seconds_left=None,
                formatted_time_left=None
            )
