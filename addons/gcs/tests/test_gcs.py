import logging

from openerp.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

class TestCloudBill(TransactionCase):
    def setUp(self):
        super(TestCloudBill, self).setUp()
        self.sale_order_model = self.registry('sale.order')

    def test_create_bill(self):
        measures = [
            {'product_id': 4, 'islive': True, 'status': 'open', 'bidpacks_qty': 1},
            {'product_id': 3, 'islive': True, 'status': 'open', 'bidpacks_qty': 1}]
        measures = []
        lines = {'lines': measures}
        record = None
        for line in lines['lines']:
            record = self.sale_order_model.cloud_bill(self.cr, self.uid, line)

        _logger.info("record %r" % record)
        self.assertIsNotNone(record)
