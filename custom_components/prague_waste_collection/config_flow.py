import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, StationType

COORD_REGEX = re.compile(r"^([0-9.]+)[NE]?\s*,\s*([0-9.]+)[NE]?$")

class PragueWasteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        existing_entries = self._async_current_entries()
        api_key_saved = next((entry.data.get("api_key") for entry in existing_entries if entry.data.get("api_key")), None)

        if user_input is not None:
            match = COORD_REGEX.match(user_input["coordinates"])
            if not match:
                errors["coordinates"] = "invalid_coords"
            else:
                lat, lon = match.groups()
                user_input["latitude"] = float(lat)
                user_input["longitude"] = float(lon)
                
                if api_key_saved and not user_input.get("api_key"):
                    user_input["api_key"] = api_key_saved

                title = f"Waste Station ({user_input['coordinates']})"
                return self.async_create_entry(title=title, data=user_input)

        data_schema = {}
        if not api_key_saved:
            data_schema[vol.Required("api_key")] = str
            
        data_schema.update({
            vol.Required("coordinates"): str,
            vol.Required("station_type", default=StationType.PUBLIC.value): vol.In(StationType.choices()),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )