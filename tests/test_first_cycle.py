import unittest
from decimal import Decimal
from risk.first_cycle import remaining_budget


class FirstCycleTests(unittest.TestCase):
    def calculate(self, **changes):
        inputs=dict(equity='51',verified_peak='51',own_cash='51',protected_cash='0',
                    existing_modeled_risk='0',reserved_cash='0',external_cash_flows='0')
        inputs.update(changes)
        return remaining_budget(**inputs)

    def test_retained_drawdown_is_stricter_than_21(self):
        result=self.calculate()
        self.assertEqual(result['maximum_additional_modeled_loss_cad'],Decimal('20.40'))
        self.assertEqual(result['binding_constraints'],['drawdown'])
        self.assertFalse(result['execution_authorized'])

    def test_drawdown_halt_boundary(self):
        self.assertEqual(self.calculate(equity='30.60',own_cash='30.60')
                         ['maximum_additional_modeled_loss_cad'],Decimal('0'))

    def test_exposure_reduces_budget(self):
        self.assertEqual(self.calculate(existing_modeled_risk='5')
                         ['maximum_additional_modeled_loss_cad'],Decimal('15.40'))

    def test_reserved_cash_cannot_be_borrowed(self):
        self.assertEqual(self.calculate(reserved_cash='50')
                         ['maximum_additional_modeled_loss_cad'],Decimal('1'))

    def test_unknown_peak_bad_amount_and_deposits_rejected(self):
        for changes in [{'verified_peak':None},{'equity':'NaN'}, {'external_cash_flows':'51'},
                        {'own_cash':'100'}, {'protected_cash':'1'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.calculate(**changes)

    def test_losses_reduce_cycle_budget_without_refill(self):
        self.assertEqual(self.calculate(equity='41',own_cash='41')
                         ['maximum_additional_modeled_loss_cad'],Decimal('10.40'))


if __name__=='__main__':
    unittest.main()
