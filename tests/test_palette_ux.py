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


def test_dirty_form_tracker_rendered(client):
    """Verify that the dirty form tracker and its initialization are rendered on the page."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function setupDirtyFormTracker()" in html
    assert "setupDirtyFormTracker();" in html


def test_shortcuts_group_and_listener_rendered(client):
    """Verify that the Keyboard Shortcuts section and the '?' keydown listener are properly rendered in base.html."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check for shortcuts group header and items
    assert 'id="shortcutsGroup"' in html
    assert 'id="shortcutsLabel"' in html
    assert 'Atajos de teclado' in html
    assert '<kbd>Alt + A</kbd>' in html
    assert '<kbd>?</kbd>' in html

    # Check for the keydown handler registering the '?' and 'Help' key
    assert "event.key === '?' || event.key === 'Help'" in html
    assert "announceToScreenReader('Ayuda de atajos de teclado abierta');" in html


def test_drag_and_drop_feedback_rendered(client):
    """Verify that the drag-and-drop feedback helper and CSS rules are rendered."""
    # Check base.html contains the helper function
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'function setupDragAndDropFeedback()' in html
    assert 'setupDragAndDropFeedback();' in html

    # Check styles.css contains the dragover styles
    response_css = client.get('/static/css/styles.css')
    assert response_css.status_code == 200
    css = response_css.get_data(as_text=True)
    assert 'input[type="file"].is-dragover' in css


def test_active_dismiss_multiplier_badge_rendered(client):
    """Verify that the active game badges render the dismiss multiplier symbol (times/x)."""
    login_session(client)
    # Get the dashboard with filters enabled
    response = client.get('/dashboard?plataforma=PC&estado=Nuevo&categoria=Biblioteca&favoritos=solo')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # When filters are active, the active badges should render "&times;" or "×" to indicate they can be dismissed
    assert '&times;' in html
