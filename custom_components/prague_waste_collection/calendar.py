from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for idx, container in enumerate(coordinator.data):
        entities.append(WasteCalendarEntity(coordinator, idx))

    async_add_entities(entities)

class WasteCalendarEntity(CoordinatorEntity, CalendarEntity):
    def __init__(self, coordinator, container_idx):
        super().__init__(coordinator)
        self.idx = container_idx

    @property
    def container_data(self):
        if self.idx < len(self.coordinator.data):
            return self.coordinator.data[self.idx]
        return None

    @property
    def unique_id(self):
        if not self.container_data:
            return None
        return f"calendar_{self.container_data['container_id']}_svoz"

    @property
    def name(self):
        if not self.container_data:
            return "Svoz odpadu"
        return f"Kalendář svozu - {self.container_data['trash_type']}"

    @property
    def event(self) -> CalendarEvent | None:
        if not self.container_data:
            return None
            
        next_pick_str = self.container_data.get("next_pick")
        if not next_pick_str:
            return None
        
        try:
            start_date = datetime.strptime(next_pick_str, "%Y-%m-%d").date()
            return CalendarEvent(
                summary=f"Svoz: {self.container_data['trash_type']}",
                start=start_date,
                end=start_date + timedelta(days=1),
                description=f"Plánované dny vývozu: {self.container_data.get('days')}"
            )
        except ValueError:
            return None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        events = []
        if self.event and start_date.date() <= self.event.start <= end_date.date():
            events.append(self.event)
        return events

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