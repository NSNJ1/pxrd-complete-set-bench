from __future__ import annotations

import unittest

from pxrd_complete_set_bench.phase_labels import phase_elements


class PhaseLabelTest(unittest.TestCase):
    def test_controlled_panel_labels_are_explicit(self) -> None:
        self.assertEqual(phase_elements("ariadnex_controlled", "A"), ("Ca", "C", "O"))
        self.assertEqual(phase_elements("ariadnex_controlled", "B"), ("Zn", "O"))

    def test_formula_prefix_is_parsed_without_duplicates(self) -> None:
        self.assertEqual(
            phase_elements("galaxi_pristine", "LiFePO4_olivine_001"),
            ("Li", "Fe", "P", "O"),
        )

    def test_unavailable_mof_identifier_returns_none(self) -> None:
        self.assertIsNone(phase_elements("rare_earth_mof", "MOF-123"))


if __name__ == "__main__":
    unittest.main()
