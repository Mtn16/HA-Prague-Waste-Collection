from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from datetime import datetime

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for idx, container in enumerate(coordinator.data):
        entities.append(WasteSensor(coordinator, idx, "trash_type", "Typ odpadu"))
        entities.append(WasteSensor(coordinator, idx, "days", "Dny vývozu"))
        entities.append(WasteSensor(coordinator, idx, "next_pick", "Příští vývoz", device_class=SensorDeviceClass.DATE))
        entities.append(WasteSensor(coordinator, idx, "last_pick", "Poslední vývoz", device_class=SensorDeviceClass.DATE))
        
        if container["is_monitored"]:
            entities.append(WasteSensor(coordinator, idx, "fill_percentage", "Úroveň naplnění", unit="%"))

    async_add_entities(entities)

class WasteSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, container_idx, key, name_suffix, device_class=None, unit=None):
        super().__init__(coordinator)
        self.idx = container_idx
        self.key = key
        self._name_suffix = name_suffix
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def container_data(self):
        if self.idx < len(self.coordinator.data):
            return self.coordinator.data[self.idx]
        return None

    @property
    def unique_id(self):
        if not self.container_data:
            return None
        return f"sensor_{self.container_data['container_id']}_{self.key}"

    @property
    def name(self):
        if not self.container_data:
            return f"Popelnice - {self._name_suffix}"
        return f"{self.container_data['trash_type']} ({self.container_data['container_id']}) - {self._name_suffix}"

    @property
    def native_value(self):
        if not self.container_data:
            return None
        
        val = self.container_data.get(self.key)
        
        if self._attr_device_class == SensorDeviceClass.DATE and val:
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except ValueError:
                return None
                
        return val

    @property
    def device_info(self) -> DeviceInfo:
        if not self.container_data:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self.container_data["container_id"])},
            name=f"Popelnice na {self.container_data['trash_type']}",
            manufacturer="Prague Waste Collection",
            model=f"Kontejner ID: {self.container_data['container_id']}",
            suggested_area=self.container_data["station_name"],
        )