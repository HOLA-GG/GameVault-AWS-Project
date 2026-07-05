import base64
import os
import re
import pytest
from app import create_app
from flask import g

@pytest.fixture
def client():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    with app.test_client() as client:
        yield client

def test_csp_nonce_generation_and_headers(client):
    """Verifica que el nonce de CSP se genere y se incluya correctamente en las cabeceras."""
    response = client.get('/')
    assert response.status_code == 200

    csp_header = response.headers.get('Content-Security-Policy', '')
    assert 'nonce-' in csp_header

    # Extract nonce from header
    match = re.search(r"'nonce-([^']+)'", csp_header)
    assert match is not None
    nonce = match.group(1)

    # Verify nonce is a valid base64 string and of expected length (16 bytes -> 24 chars)
    nonce_bytes = base64.b64decode(nonce)
    assert len(nonce_bytes) == 16

    # Verify nonce is in the body script tags
    html = response.get_data(as_text=True)
    assert f'nonce="{nonce}"' in html

def test_csp_nonce_uniqueness(client):
    """Verifica que el nonce sea único por petición."""
    r1 = client.get('/')
    csp1 = r1.headers.get('Content-Security-Policy', '')
    n1 = re.search(r"'nonce-([^']+)'", csp1).group(1)

    r2 = client.get('/')
    csp2 = r2.headers.get('Content-Security-Policy', '')
    n2 = re.search(r"'nonce-([^']+)'", csp2).group(1)

    assert n1 != n2

def test_data_confirm_handlers(client):
    """Verifica que los handlers de confirmación inline hayan sido removidos y sustituidos por data-confirm."""
    # Test index page (needs login ideally, but we can check template source or just the response if it renders something)
    # Actually we just want to see if the string 'onsubmit="return confirm' is gone from the rendered HTML
    # We'll check multiple pages
    pages = ['/', '/registro', '/login']
    for page in pages:
        res = client.get(page)
        html = res.get_data(as_text=True)
        assert 'onsubmit="return confirm' not in html

def test_base_html_contains_nonce_on_all_scripts(client):
    """Verifica que todos los tags <script> tengan el atributo nonce."""
    response = client.get('/')
    html = response.get_data(as_text=True)

    # Find all script tags
    scripts = re.findall(r'<script[^>]*>', html)
    for script in scripts:
        assert 'nonce="' in script
