from __future__ import annotations

import sys
from pathlib import Path
import pytest
from tests.test_app import app, client, login_session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_accessibility_toggle_shortcuts_rendered(client):
    """Verify that the accessibility tools toggle button has the new shortcut and ARIA attributes."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check that the toggle button has the Alt+A hint in title and aria-keyshortcuts
    assert 'title="Herramientas de accesibilidad (Alt + A)"' in html
    assert 'aria-keyshortcuts="Alt+A"' in html


def test_dashboard_title_shortcut_hint_rendered(client):
    """Verify that the game form title input on the dashboard has the 'N' shortcut hint and attributes."""
    login_session(client)
    response = client.get('/dashboard')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check that the Title label has the (Presiona N) hint
    assert '(Presiona <kbd>N</kbd>)' in html
    # Check that the Title input has the aria-describedby attribute linked to the hint
    assert 'aria-describedby="title-hint"' in html


def test_copy_tooltip_delegation_rendered(client):
    """Verify that both mouseover and focusin handlers are registered for the copy tooltip progressive helper."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "document.addEventListener('mouseover', syncCopyTooltip);" in html
    assert "document.addEventListener('focusin', syncCopyTooltip);" in html
