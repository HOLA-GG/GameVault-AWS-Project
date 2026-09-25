"""Tests for Bolt optimization in aplicar_ratings_showcase."""

import unittest
from unittest.mock import patch


class TestBoltRatingsOptimization(unittest.TestCase):
    """Verifica que la optimización de short-circuit en aplicar_ratings_showcase sea exacta."""

    @patch('app.models.obtener_ratings_multiple')
    def test_aplicar_ratings_showcase_without_baseline(self, mock_get_ratings):
        """Verifica el camino optimizado sin default_rating_key (p. ej. colecciones públicas)."""
        from app.models import aplicar_ratings_showcase

        mock_get_ratings.return_value = {
            'user-1': {'average': 4.8, 'votes_count': 15},
            'user-2': {'average': 3.5, 'votes_count': 2},
        }

        items = [
            {'user_id': 'user-1', 'title': 'Colección 1'},
            {'user_id': 'user-2', 'title': 'Colección 2'},
            {'user_id': 'user-3', 'title': 'Colección 3'},
        ]

        result = aplicar_ratings_showcase(
            items,
            subject_type='public',
            subject_id_key='user_id',
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['showcase_rating_average'], 4.8)
        self.assertEqual(result[0]['showcase_votes_count'], 15)
        self.assertEqual(result[1]['showcase_rating_average'], 3.5)
        self.assertEqual(result[1]['showcase_votes_count'], 2)
        self.assertIsNone(result[2]['showcase_rating_average'])
        self.assertEqual(result[2]['showcase_votes_count'], 0)

    @patch('app.models.obtener_ratings_multiple')
    def test_aplicar_ratings_showcase_with_baseline(self, mock_get_ratings):
        """Verifica la compatibilidad cuando se especifican default_rating_key y default_votes_key (p. ej. samples)."""
        from app.models import aplicar_ratings_showcase

        mock_get_ratings.return_value = {
            'sample-1': {'average': 5.0, 'votes_count': 5},
            'sample-2': {'average': None, 'votes_count': 0},
        }

        items = [
            {'id': 'sample-1', 'base_avg': 4.0, 'base_votes': 10},
            {'id': 'sample-2', 'base_avg': 4.5, 'base_votes': 8},
        ]

        result = aplicar_ratings_showcase(
            items,
            subject_type='sample',
            subject_id_key='id',
            default_rating_key='base_avg',
            default_votes_key='base_votes',
        )

        self.assertEqual(len(result), 2)
        # sample-1: (4.0 * 10 + 5.0 * 5) / 15 = 65 / 15 = 4.333 -> 4.3
        self.assertEqual(result[0]['showcase_rating_average'], 4.3)
        self.assertEqual(result[0]['showcase_votes_count'], 15)
        # sample-2: no actual votes -> baseline 4.5 and 8 votes
        self.assertEqual(result[1]['showcase_rating_average'], 4.5)
        self.assertEqual(result[1]['showcase_votes_count'], 8)

    def test_empty_items(self):
        """Verifica comportamiento cuando la lista de items está vacía."""
        from app.models import aplicar_ratings_showcase

        self.assertEqual(aplicar_ratings_showcase([], subject_type='public', subject_id_key='user_id'), [])


if __name__ == '__main__':
    unittest.main()
