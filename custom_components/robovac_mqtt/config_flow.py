import logging
import random
import string
from typing import Any, Optional

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from voluptuous import Required, Schema

from .constants.hass import DOMAIN, VACS
from .EufyClean import EufyClean

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = Schema(
    {
        Required(CONF_USERNAME): cv.string,
        Required(CONF_PASSWORD): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eufy Robovac."""

    data: Optional[dict[str, Any]]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)
        errors = {}
        try:
            username = user_input[CONF_USERNAME]
            _LOGGER.info("Trying to login with username: {}".format(username))
            unique_id = username
            
            eufy_clean = EufyClean(username, user_input[CONF_PASSWORD])
            await eufy_clean.init()
            
            if not eufy_clean.eufyCleanApi.eufyApi.session:
                errors["base"] = "invalid_auth"
            else:
                # Check for unsupported devices during setup
                unsupported = eufy_clean.eufyCleanApi.unsupported_devices
                if unsupported:
                    device_names = ", ".join([d.get('alias_name', d.get('name', 'Unknown')) for d in unsupported])
                    self.hass.components.persistent_notification.async_create(
                        f"The following Eufy devices in your account do not support the newer MQTT protocol and were not added: "
                        f"{device_names}. "
                        "These likely use the legacy Tuya-based protocol which this integration does not support.",
                        title="Unsupported Eufy Devices Detected",
                        notification_id="eufy_unsupported_devices"
                    )

                data = user_input.copy()
                data[VACS] = {}
                return self.async_create_entry(title=unique_id, data=user_input)
        except Exception as e:
            _LOGGER.exception("Unexpected exception: {}".format(e))
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return True
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )
