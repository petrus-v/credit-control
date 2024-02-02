# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountFullReconcile(models.Model):
    _inherit = "account.full.reconcile"

    sent_to_upflow = fields.Boolean(
        default=False,
        help=(
            "Technical field to remove in next version used "
            "to migrate from full reconcile synced to partial.",
        ),
    )
