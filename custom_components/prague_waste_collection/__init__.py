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
                container_id = container.get("id")
                if not container_id:
                    continue

                trash_type = container.get("trash_type", {}).get("description", "Neznámý")
                if trash_type == "Multikomoditní sběr":
                    trash_type = "Plast"

                days = container.get("cleaning_days")
                next_pick = container.get("next_cleaning_date")
                last_pick = container.get("last_cleaning_date")
                
                if next_pick and "T" in next_pick:
                    next_pick = next_pick.split("T")[0]
                if last_pick and "T" in last_pick:
                    last_pick = last_pick.split("T")[0]

                is_monitored = container.get("is_monitored", False)
                
                fill_percentage = None
                if is_monitored:
                    last_meas = container.get("last_measurement")
                    if last_meas and isinstance(last_meas, dict):
                        fill_percentage = last_meas.get("fill_percentage")

                cleaned_container = {
                    "station_id": station_id,
                    "station_name": station_name,
                    "container_id": str(container_id),
                    "trash_type": trash_type,
                    "days": days if days else "Neuvedeno",
                    "next_pick": next_pick,
                    "last_pick": last_pick,
                    "is_monitored": is_monitored,
                    "fill_percentage": fill_percentage
                }
                containers.append(cleaned_container)
        
        _LOGGER.debug("Zpracováno %d kontejnerů z Golemio API", len(containers))
        return containers