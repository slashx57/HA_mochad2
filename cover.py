"""Support for X10 shutter over Mochad."""
from pymochad import device
import logging
import voluptuous as vol

from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    PLATFORM_SCHEMA,
    CoverEntity,
)
from homeassistant.const import CONF_ADDRESS, CONF_DEVICES, CONF_NAME, CONF_PLATFORM
from homeassistant.helpers import config_validation as cv

from . import CONF_COMM_TYPE, DOMAIN, REQ_LOCK

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): DOMAIN,
        CONF_DEVICES: [
            {
                vol.Optional(CONF_NAME): cv.string,
                vol.Required(CONF_ADDRESS): cv.x10_address,
                vol.Optional(CONF_COMM_TYPE): cv.string,
            }
        ],
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up X10 over a mochad controller."""
    mochad_controller = hass.data[DOMAIN]
    devs = config.get(CONF_DEVICES)
    add_entities([MochadCover(hass, mochad_controller.ctrl, dev) for dev in devs])
    return True



class MochadCover(CoverEntity):
    """Representation a command line cover."""

    def __init__(self, hass, ctrl, dev):

        """Initialize the cover."""
        self._controller = ctrl
        self._address = dev[CONF_ADDRESS]
        self._name = dev.get(CONF_NAME, f"x10_shutter_dev_{self._address}")
        self._comm_type = dev.get(CONF_COMM_TYPE, "pl")
        self.shutter = device.Device(ctrl, self._address, comm_type=self._comm_type)
        self._current_position = None

    @property
    def current_cover_position(self):
        """Return current position of cover.
        
        None is unknown, 0 is closed, 100 is fully open.
        """
        if self._current_position is not None:
            if self._current_position <= 5:
                return 0
            if self._current_position >= 95:
                return 100
            return self._current_position

    def _get_device_status(self):
        """Get the status from mochad."""
        with REQ_LOCK:
            status = self.shutter.get_status().rstrip()
        return status == "on"

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0

    @property
    def supported_features(self):
        """Return supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    # @property
    # def assumed_state(self):
        # """X10 devices are normally 1-way so we have to assume the state."""
        # return True

    def open_cover(self, **kwargs):
        """Open the cover."""
        with REQ_LOCK:
            self.shutter.send_cmd("on")
        self._current_position = 100

    def close_cover(self, **kwargs):
        """Close the cover."""
        with REQ_LOCK:
            self.shutter.send_cmd("off")
        self._current_position = 0

    def set_cover_position(self, **kwargs):
       """Move the cover to a specific position."""
       mochad_level = int(25 * float(kwargs.get(ATTR_POSITION)) / 100)
       with REQ_LOCK:
            self.shutter.send_cmd(f"extended_code_1 0 3 {mochad_level}")
       self._current_position = kwargs.get(ATTR_POSITION)

