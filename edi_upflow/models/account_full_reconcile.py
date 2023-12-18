# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _name = "account.full.reconcile"
    _inherit = ["account.full.reconcile", "mail.thread", "edi.exchange.consumer.mixin"]

    sent_to_upflow = fields.Boolean(
        default=False,
        help="Technical field to know if the record has been synchronized with upflow",
    )
