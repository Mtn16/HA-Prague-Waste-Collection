import logging
import aiohttp
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = GolemioDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "calendar"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "calendar"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class GolemioDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name="Prague Waste Collection",
            update_interval=timedelta(hours=6),
        )
        self.entry = entry

    async def _async_update_data(self):
        api_key = self.entry.data.get("api_key")
        lat = self.entry.data.get("latitude")
        lon = self.entry.data.get("longitude")
        station_type = self.entry.data.get("station_type")

        url = f"https://api.golemio.cz/v2/sortedwastestations?latlng={lat},{lon}&range=10&accessibility={station_type}"
        headers = {
            "X-Access-Token": api_key,
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error communication with Golemio API: {response.status}")
                    
                    data = await response.json()
                    return self._process_golemio_data(data)
            except Exception as err:
                raise UpdateFailed(f"Server disconnected or error: {err}")

    def _process_golemio_data(self, data):
        features = data.get("features", [])
        containers = []

        for feature in features:
            props = feature.get("properties", {})
            station_id = props.get("id")
            station_name = props.get("name", f"Stanice {station_id}")

            for container in props.get("containers", []):
                trash_type = container.get("trash_type", {}).get("description", "Neznámý")
                if trash_type == "Multikomoditní sběr":
                    trash_type = "Plast"

                cleaned_container = {
                    "station_id": station_id,
                    "station_name": station_name,
                    "container_id": container.get("id"),
                    "trash_type": trash_type,
                    "days": container.get("cleaning_days"),
                    "next_pick": container.get("next_cleaning_date"),
                    "last_pick": container.get("last_cleaning_date"),
                    "is_monitored": container.get("is_monitored"),
                    "fill_percentage": container.get("last_measurement", {}).get("fill_percentage") if container.get("is_monitored") else None
                }
                containers.append(cleaned_container)
        
        return containers