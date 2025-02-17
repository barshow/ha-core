"""Define tests for the QNAP QSW config flow."""

from unittest.mock import MagicMock, patch

from aioqsw.const import API_MAC_ADDR, API_PRODUCT, API_RESULT
from aioqsw.exceptions import LoginError, QswError

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import dhcp
from homeassistant.components.qnap_qsw.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from .util import CONFIG, LIVE_MOCK, SYSTEM_BOARD_MOCK, USERS_LOGIN_MOCK

from tests.common import MockConfigEntry

DHCP_SERVICE_INFO = dhcp.DhcpServiceInfo(
    hostname="qsw-m408-4c",
    ip="192.168.1.200",
    macaddress="245EBE000000",
)

TEST_PASSWORD = "test-password"
TEST_URL = "test-url"
TEST_USERNAME = "test-username"


async def test_form(hass: HomeAssistant) -> None:
    """Test that the form is served with valid input."""

    with patch(
        "homeassistant.components.qnap_qsw.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry, patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ), patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_system_board",
        return_value=SYSTEM_BOARD_MOCK,
    ), patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.post_users_login",
        return_value=USERS_LOGIN_MOCK,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == SOURCE_USER
        assert result["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

        await hass.async_block_till_done()

        conf_entries = hass.config_entries.async_entries(DOMAIN)
        entry = conf_entries[0]
        assert entry.state is ConfigEntryState.LOADED

        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert (
            result["title"]
            == f"QNAP {SYSTEM_BOARD_MOCK[API_RESULT][API_PRODUCT]} {SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]}"
        )
        assert result["data"][CONF_URL] == CONFIG[CONF_URL]
        assert result["data"][CONF_USERNAME] == CONFIG[CONF_USERNAME]
        assert result["data"][CONF_PASSWORD] == CONFIG[CONF_PASSWORD]

        assert len(mock_setup_entry.mock_calls) == 1


async def test_form_duplicated_id(hass: HomeAssistant) -> None:
    """Test setting up duplicated entry."""

    system_board = MagicMock()
    system_board.get_mac = MagicMock(
        return_value=SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG,
        unique_id=format_mac(SYSTEM_BOARD_MOCK[API_RESULT][API_MAC_ADDR]),
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        return_value=system_board,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_form_unique_id_error(hass: HomeAssistant):
    """Test unique ID error."""

    system_board = MagicMock()
    system_board.get_mac = MagicMock(return_value=None)

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        return_value=system_board,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["type"] == "abort"
        assert result["reason"] == "invalid_id"


async def test_connection_error(hass: HomeAssistant):
    """Test connection to host error."""

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        side_effect=QswError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {CONF_URL: "cannot_connect"}


async def test_login_error(hass: HomeAssistant):
    """Test login error."""

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        side_effect=LoginError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CONFIG
        )

        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}


async def test_dhcp_flow(hass: HomeAssistant) -> None:
    """Test that DHCP discovery works."""
    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "discovered_connection"

    with patch(
        "homeassistant.components.qnap_qsw.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry, patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ), patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_system_board",
        return_value=SYSTEM_BOARD_MOCK,
    ), patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.post_users_login",
        return_value=USERS_LOGIN_MOCK,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_dhcp_flow_error(hass: HomeAssistant) -> None:
    """Test that DHCP discovery fails."""

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        side_effect=QswError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "cannot_connect"


async def test_dhcp_connection_error(hass: HomeAssistant):
    """Test DHCP connection to host error."""

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "discovered_connection"

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        side_effect=QswError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["errors"] == {CONF_URL: "cannot_connect"}


async def test_dhcp_login_error(hass: HomeAssistant):
    """Test DHCP login error."""

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.get_live",
        return_value=LIVE_MOCK,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            data=DHCP_SERVICE_INFO,
            context={"source": config_entries.SOURCE_DHCP},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "discovered_connection"

    with patch(
        "homeassistant.components.qnap_qsw.QnapQswApi.validate",
        side_effect=LoginError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: TEST_USERNAME,
                CONF_PASSWORD: TEST_PASSWORD,
            },
        )

        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}
