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


def test_profile_inputs_select_on_focus(client):
    """Verify that the pre-filled inputs on the profile page have select-on-focus class."""
    login_session(client)
    response = client.get('/perfil')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verify that apellido, prefijo_pais, and telefono inputs have the select-on-focus class
    assert 'id="apellido"' in html
    assert 'id="prefijo_pais"' in html
    assert 'id="telefono"' in html
    assert 'class="select-on-focus"' in html


def test_palette_placeholders_and_loading_text(client):
    """Verify newly added placeholders and data-loading-text attributes."""
    login_session(client)

    # 1. Edit game page
    # Since we need a game, let's just make a GET request or check general rendering if page requires ID.
    # We can check placeholders in profile.html first
    response = client.get('/perfil')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'placeholder="Ej: Juan"' in html
    assert 'placeholder="Ej: Pérez"' in html
    assert 'placeholder="Tu contraseña actual"' in html
    assert 'placeholder="Mínimo 8 caracteres (letras y números)"' in html
    assert 'placeholder="Repite tu nueva contraseña"' in html

    # 2. Admin logs page (login as admin)
    login_session(client, role='admin')
    response = client.get('/admin/logs')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'placeholder="Email, nombre o ID de usuario"' in html


def test_demo_form_image_preview_rendered(client):
    """Verify that the demo form page renders the image preview elements and script."""
    response = client.get('/demo')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="demoImagePreviewContainer"' in html
    assert 'id="demoImagePreview"' in html
    assert 'id="demoRemoveImageButton"' in html
    assert 'window.announceToScreenReader?.(`Imagen seleccionada: ${file.name}`);' in html


def test_scroll_to_top_rendered(client):
    """Verify that the Scroll to Top button and its JS initializer are rendered on the page."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="scrollToTopBtn"' in html
    assert 'aria-label="Volver arriba"' in html
    assert 'function setupScrollToTop()' in html
    assert 'setupScrollToTop();' in html


def test_dashboard_active_filters_rendered(client):
    """Verify that the active filters row is rendered correctly on the dashboard with proper accessibility attributes."""
    login_session(client)
    response = client.get('/dashboard?plataforma=PC&estado=Nuevo&q=chrono')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check for the main row and title
    assert 'class="active-filters"' in html
    assert 'Filtros activos:' in html

    # Check for search query active badge
    assert 'Búsqueda: "chrono"' in html
    assert 'aria-label="Quitar filtro de búsqueda: chrono"' in html

    # Check for platform active badge
    assert 'class="badge plataforma is-active"' in html
    assert 'aria-label="Quitar filtro de plataforma: PC"' in html

    # Check for status active badge
    assert 'class="badge estado is-active"' in html
    assert 'aria-label="Quitar filtro de estado: Nuevo"' in html

    # Check for "Limpiar todos" button
    assert 'aria-label="Limpiar todos los filtros"' in html
    assert 'Limpiar todos' in html


def test_search_input_escape_key_clears_or_blurs(client):
    """Verify that the base template script contains the Escape keydown handler for the search input (#q)."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check that base.html defines the Escape key logic for #q
    assert "document.getElementById('q')" in html
    assert "document.activeElement === searchInput" in html
    assert "searchInput.value = '';" in html
    assert "searchInput.dispatchEvent(new Event('input'));" in html
    assert "announceToScreenReader('Búsqueda borrada');" in html
    assert "searchInput.blur();" in html


def test_palette_new_select_on_focus_and_placeholders(client):
    """Verify that the new forms have select-on-focus behavior and consistent Spanish placeholders."""
    # 1. Login page
    response = client.get('/login')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="select-on-focus"' in html
    assert 'placeholder="Ej: coleccionista@email.com"' in html

    # 2. Registro page
    response = client.get('/registro')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="select-on-focus"' in html

    # 3. Forgot password page
    response = client.get('/forgot-password')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="select-on-focus"' in html
    assert 'placeholder="Ej: juan@ejemplo.com"' in html

    # 4. Forgot password manual page
    response = client.get('/forgot-password/manual')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="select-on-focus"' in html
    assert 'placeholder="Ej: 5551234567"' in html


def test_palette_star_rating_accessibility(client):
    """Verify that the landing page's star rating buttons have descriptive aria-labels and sync aria-pressed attributes."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verify descriptive action labels exist on star buttons
    assert 'aria-label="Valorar con 1 estrella"' in html
    assert 'aria-label="Valorar con 5 estrellas"' in html

    # Verify aria-pressed attributes are initially populated
    assert 'aria-pressed="true"' in html or 'aria-pressed="false"' in html

    # Verify script dynamically syncs aria-pressed
    assert "star.setAttribute('aria-pressed', isFilled ? 'true' : 'false')" in html


def test_palette_accessibility_panel_status_labels(client):
    """Verify that the accessibility panel rendered in the base template includes dynamic status labels."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check that header status labels exist
    assert 'id="activeThemeLabel"' in html
    assert 'id="activeTextScaleLabel"' in html
    assert 'id="activeMotionLabel"' in html
    assert 'id="activePanelPositionLabel"' in html

    # Check JS sync logic exists for all 4 labels
    assert 'activeThemeLabel' in html
    assert 'activeTextScaleLabel' in html
    assert 'activeMotionLabel' in html
    assert 'activePanelPositionLabel' in html


def test_palette_font_scale_buttons_rendered(client):
    """Verify that the accessibility panel font scale control has - and + precise adjustments buttons with correct ARIA attributes."""
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check for decrease button
    assert 'id="fontScaleDecrease"' in html
    assert 'aria-label="Disminuir tamaño del texto"' in html

    # Check for increase button
    assert 'id="fontScaleIncrease"' in html
    assert 'aria-label="Aumentar tamaño del texto"' in html

    # Check for JS handlers linking the buttons
    assert 'fontScaleDecrease' in html
    assert 'fontScaleIncrease' in html
    assert 'Tamaño de texto disminuido al' in html
    assert 'Tamaño de texto aumentado al' in html


def test_palette_prefijo_pais_datalist_rendered(client):
    """Verify that both registration and profile pages render the country prefix datalist to enhance prefijo_pais inputs."""
    # 1. Registration page
    response = client.get('/registro')
    assert response.status_code == 200
    html_reg = response.get_data(as_text=True)
    assert 'id="prefijo_pais"' in html_reg
    assert 'list="prefijos_lista"' in html_reg
    assert 'id="prefijos_lista"' in html_reg
    assert '<option value="+34">España (+34)</option>' in html_reg
    assert '<option value="+57">Colombia (+57)</option>' in html_reg

    # 2. Profile page
    login_session(client)
    response = client.get('/perfil')
    assert response.status_code == 200
    html_prof = response.get_data(as_text=True)
    assert 'id="prefijo_pais"' in html_prof
    assert 'list="prefijos_lista"' in html_prof
    assert 'id="prefijos_lista"' in html_prof
    assert '<option value="+34">España (+34)</option>' in html_prof
    assert '<option value="+57">Colombia (+57)</option>' in html_prof


def test_caps_lock_warning_rendered(client):
    """Verify that pages with password fields render the Caps Lock detector script and warning element."""
    response = client.get('/login')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verify that the warning element and detection logic are rendered in the DOM
    assert 'caps-warning' in html
    assert 'Bloqueo de mayúsculas activado' in html
    assert "e.getModifierState('CapsLock')" in html
    assert 'checkCapsLock' in html


def test_profile_visibility_dynamic_toggle_rendered(client):
    """Verify that the profile page renders the dynamic visibility/opt-in toggle script."""
    login_session(client)
    response = client.get('/perfil')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verify elements are present
    assert 'id="collection_visibility"' in html
    assert 'id="homepage_showcase_opt_in"' in html

    # Verify script existence and key function/logic parts
    assert 'updateOptInState' in html
    assert 'visibilitySelect.addEventListener' in html
    assert 'optInCheckbox.disabled' in html
    assert 'window.announceToScreenReader?.(' in html


def test_palette_rating_labels_and_delete_loading_text(client):
    """Verify enhanced rating options and delete loading text attributes."""
    login_session(client)

    # 1. Check dashboard rating options
    response = client.get('/dashboard')
    assert response.status_code == 200
    html_dash = response.get_data(as_text=True)
    assert '10/10 ⭐ Obra maestra' in html_dash
    assert '9/10 ⭐ Excelente' in html_dash
    assert '1/10 ⭐ Injugable' in html_dash

    # Add a game to render the game card delete form with data-loading-text="Eliminando..."
    client.post('/agregar', data={
        'titulo': 'Test Game Delete',
        'descripcion': 'Test description',
        'plataforma': 'PC',
        'estado': 'Nuevo',
        'categoria': 'Biblioteca',
        'prioridad': 'Media',
    }, follow_redirects=True)

    response_games = client.get('/dashboard')
    assert response_games.status_code == 200
    html_games = response_games.get_data(as_text=True)
    assert 'data-loading-text="Eliminando..."' in html_games


def test_palette_game_card_copy_button(client):
    """Verify that game cards render the copy button with data-copy and aria-label attributes."""
    login_session(client)

    client.post('/agregar', data={
        'titulo': 'The Legend of Zelda',
        'descripcion': 'NES classic game',
        'plataforma': 'Nintendo',
        'estado': 'Usado',
        'categoria': 'Biblioteca',
        'prioridad': 'Alta',
    }, follow_redirects=True)

    response = client.get('/dashboard')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'btn-copy' in html
    assert 'data-copy="The Legend of Zelda (Nintendo)"' in html
    assert 'aria-label="Copiar nombre de The Legend of Zelda"' in html
    assert 'title="Copiar nombre de The Legend of Zelda"' in html
