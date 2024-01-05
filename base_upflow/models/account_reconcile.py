# Copyright 2023-2024 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# @author Damien Crier <damien.crier@foodles.co>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountUpflowReconcileAbstract(models.AbstractModel):
    _name = "account.upflow.reconcile.abstract"
    _desc = "Abstract model to have same methods for full and partial reconcile"

    def _prepare_reconcile_payload(self):
        payload = {
            "externalId": str(self.id),
            "invoices": [],
            "payments": [],
            "creditNotes": [],
            "refunds": [],
        }
        return payload

    def _get_partial_records(self):
        raise NotImplementedError

    def get_upflow_api_post_reconcile_payload(self):
        """expect to be called from account move type:

        * customer invoice
        * customer refund

        Once there are considered partially/fully paid
        """
        payload = self._prepare_reconcile_payload()
        for partial in self._get_partial_records():
            data = {
                "externalId": str(partial.debit_move_id.move_id.id),
                "amountLinked": partial.company_currency_id.to_lowest_division(
                    partial.amount
                ),
            }
            if partial.debit_move_id.move_id.upflow_uuid:
                data["id"] = partial.debit_move_id.move_id.upflow_uuid
            if partial.debit_move_id.move_id.move_type == "out_invoice":
                kind = "invoices"
                data["customId"] = partial.debit_move_id.move_id.name
            else:
                kind = "refunds"

            payload[kind].append(data)

            data = {
                "externalId": str(partial.credit_move_id.move_id.id),
                "amountLinked": partial.company_currency_id.to_lowest_division(
                    partial.amount
                ),
            }
            if partial.credit_move_id.move_id.upflow_uuid:
                data["id"] = partial.credit_move_id.move_id.upflow_uuid
            if partial.credit_move_id.move_id.move_type == "out_refund":
                kind = "creditNotes"
                data["customId"] = partial.credit_move_id.move_id.name
            else:
                kind = "payments"

            payload[kind].append(data)

        return payload


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _inherit = ["account.partial.reconcile", "account.upflow.reconcile.abstract"]

    def _get_partial_records(self):
        return self


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _inherit = ["account.full.reconcile", "account.upflow.reconcile.abstract"]

    def _get_partial_records(self):
        return self.partial_reconcile_ids
