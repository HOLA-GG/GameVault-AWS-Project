from __future__ import annotations

import sys
from pathlib import Path
import pytest
from flask import Flask, g

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routes import build_query_args

def test_build_query_args_no_request_context():
    """Verify build_query_args works correctly outside a request context (falls back to empty dict)."""
    assert build_query_args() == {}
    assert build_query_args(q='test', page='2') == {'q': 'test', 'page': '2'}

def test_build_query_args_with_request_context():
    """Verify build_query_args works with request context and caches results in g."""
    app = Flask(__name__)

    with app.test_request_context('/?q=chrono&plataforma=PC'):
        # On first call, base_args should be created
        res1 = build_query_args(page='2')
        assert res1 == {'q': 'chrono', 'plataforma': 'PC', 'page': '2'}
        assert hasattr(g, '_query_args_base')
        assert g._query_args_base == {'q': 'chrono', 'plataforma': 'PC'}

        # Second call should reuse the cache and avoid re-converting request.args
        res2 = build_query_args(categoria='Backlog')
        assert res2 == {'q': 'chrono', 'plataforma': 'PC', 'categoria': 'Backlog'}

        # Verify pops/deletes
        res3 = build_query_args(q=None, plataforma='')
        assert res3 == {}
