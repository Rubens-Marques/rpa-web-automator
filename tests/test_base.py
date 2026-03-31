import pytest
from unittest.mock import MagicMock, patch
from src.rpa.base import WebAutomator


def test_automator_initializes():
    with patch("src.rpa.base.webdriver.Chrome"):
        automator = WebAutomator(headless=True)
    assert automator is not None


def test_automator_context_manager():
    mock_driver = MagicMock()
    with patch("src.rpa.base.webdriver.Chrome", return_value=mock_driver):
        with WebAutomator(headless=True) as automator:
            assert automator.driver is not None
    mock_driver.quit.assert_called_once()


def test_safe_find_returns_none_when_not_found():
    mock_driver = MagicMock()
    mock_driver.find_element.side_effect = Exception("not found")
    with patch("src.rpa.base.webdriver.Chrome", return_value=mock_driver):
        automator = WebAutomator(headless=True)
        result = automator.safe_find("css selector", "#nonexistent")
    assert result is None
