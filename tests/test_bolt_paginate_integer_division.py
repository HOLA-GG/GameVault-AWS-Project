"""
tests/test_bolt_paginate_integer_division.py - Tests for fast integer division pagination optimization.
"""

from __future__ import annotations

import math
import pytest
from app import create_app
from app.routes import paginate_items


def test_paginate_items_integer_division_equivalence():
    """Verifica la equivalencia matemática entre math.ceil y la división entera."""
    for total in range(0, 500):
        for per_page in range(0, 50):
            expected = max(1, math.ceil(total / per_page)) if per_page else 1
            actual = max(1, (total + per_page - 1) // per_page) if per_page else 1
            assert actual == expected, f"Desajuste para total={total}, per_page={per_page}"


def test_paginate_items_empty_list():
    """Verifica paginación con lista vacía."""
    res = paginate_items([], page=1, per_page=12)
    assert res['total_items'] == 0
    assert res['total_pages'] == 1
    assert res['page'] == 1
    assert res['items'] == []
    assert res['has_prev'] is False
    assert res['has_next'] is False


def test_paginate_items_exact_multiples():
    """Verifica paginación con múltiplos exactos de per_page."""
    items = list(range(50))
    res = paginate_items(items, page=1, per_page=25)
    assert res['total_items'] == 50
    assert res['total_pages'] == 2
    assert res['page'] == 1
    assert len(res['items']) == 25
    assert res['has_prev'] is False
    assert res['has_next'] is True


def test_paginate_items_non_exact_multiples():
    """Verifica paginación con múltiplos no exactos de per_page."""
    items = list(range(51))
    res = paginate_items(items, page=3, per_page=25)
    assert res['total_items'] == 51
    assert res['total_pages'] == 3
    assert res['page'] == 3
    assert len(res['items']) == 1
    assert res['items'] == [50]
    assert res['has_prev'] is True
    assert res['has_next'] is False


def test_paginate_items_zero_per_page():
    """Verifica fallback seguro cuando per_page es 0."""
    items = list(range(10))
    res = paginate_items(items, page=1, per_page=0)
    assert res['total_pages'] == 1
    assert res['page'] == 1


def test_admin_pagination_routes(monkeypatch):
    """Verifica que las rutas administrativas paginadas funcionan correctamente."""
    monkeypatch.setenv('APP_ENV', 'testing')
    app = create_app()
    client = app.test_client()
    resp = client.get('/admin')
    assert resp.status_code == 302
