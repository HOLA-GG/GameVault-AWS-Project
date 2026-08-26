"""
tests/test_bolt_ratings_optimization.py - Regression and correctness tests for
the optimized combinar_rating_showcase and aplicar_ratings_showcase functions.
"""

from app.models import aplicar_ratings_showcase, combinar_rating_showcase


def test_combinar_rating_showcase_pure_actual():
    summary = {'average': 4.5, 'votes_count': 10}
    res = combinar_rating_showcase(summary)
    assert res['average'] == 4.5
    assert res['votes_count'] == 10


def test_combinar_rating_showcase_pure_baseline():
    summary = {'average': None, 'votes_count': 0}
    res = combinar_rating_showcase(summary, base_average=8.0, base_votes_count=5)
    assert res['average'] == 8.0
    assert res['votes_count'] == 5


def test_combinar_rating_showcase_merged():
    summary = {'average': 4.0, 'votes_count': 10}
    # (4.0 * 10 + 5.0 * 10) / 20 = 4.5
    res = combinar_rating_showcase(summary, base_average=5.0, base_votes_count=10)
    assert res['average'] == 4.5
    assert res['votes_count'] == 20


def test_aplicar_ratings_showcase_empty():
    res = aplicar_ratings_showcase([], subject_type='sample', subject_id_key='id')
    assert res == []


def test_aplicar_ratings_showcase_batch():
    items = [
        {'id': 'sample_1', 'average_rating': 4.5, 'base_votes_count': 10},
        {'id': 'sample_2', 'average_rating': 3.0, 'base_votes_count': 5},
    ]

    res = aplicar_ratings_showcase(
        items,
        subject_type='sample',
        subject_id_key='id',
        default_rating_key='average_rating',
        default_votes_key='base_votes_count',
    )

    assert len(res) == 2
    for item in res:
        assert 'showcase_rating_average' in item
        assert 'showcase_votes_count' in item
        assert item['showcase_votes_count'] >= 5
