import logging

from openerp.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

class TestLivebid(TransactionCase):
    def setUp(self):
        super(TestLivebid, self).setUp()
        self.cheape_livebid_model = self.registry('cheape.livebid')

    def test_create_livebid(self):
        livebids = [
            {'product_id': 4, 'islive': True, 'status': 'open', 'bidpacks_qty': 1},
            {'product_id': 3, 'islive': True, 'status': 'open', 'bidpacks_qty': 1}]
        record = None
        for livebid in livebids:
            record = self.cheape_livebid_model.create(self.cr, self.uid, livebid)

        _logger.info("record %r" % record)
        self.assertIsNotNone(record)

    def test_livebid_countdown_list(self):
        cr, uid = self.cr, self.uid
        countdowns = self.cheape_livebid_model.search(cr, uid, [])
        _logger.info("record %r" % len(countdowns))
        self.assertIsNotNone(countdowns)
