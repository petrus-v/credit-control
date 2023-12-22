# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

logger = logging.getLogger(__name__)


class AccountFullReconcileUpflowEventListener(Component):

    _name = "account.full.reconcile.upflow.event.listener"
    _inherit = "base.upflow.event.listener"
    _apply_on = ["account.full.reconcile"]

    def _filter_relevant_account_event_state_method(self, states):
        """Only accounting event (ignore pdf events)"""
        event_types = (
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_invoices"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_credit_notes"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_payments"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_refunds"),
        )
        return (
            lambda ex, event_types=event_types, states=states: ex.type_id in event_types
            and ex.edi_exchange_state in states
        )

    def _ensure_related_move_is_synced(self, reconcile_exchange, move, exchange_type):
        "output_sent_and_processed"
        ongoing_move_exchanges = move.exchange_record_ids.filtered(
            self._filter_relevant_account_event_state_method(
                [
                    "new",
                    "output_pending",
                    "output_sent",
                ]
            )
        )
        finalized_move_exchanges = move.exchange_record_ids.filtered(
            self._filter_relevant_account_event_state_method(
                [
                    "output_sent_and_processed",
                ]
            )
        )
        if move.upflow_uuid or ongoing_move_exchanges:
            # we don't know if an error happens on the first exchange
            # then user manage to create an other exchange that passed
            # we only link on going exchange and processed
            # and there is a good change that the event will raise anyway
            reconcile_exchange.dependent_exchange_ids |= (
                ongoing_move_exchanges | finalized_move_exchanges
            )
        else:
            self._create_missing_exchange_record(
                reconcile_exchange, move, exchange_type
            )

    def _create_missing_exchange_record(self, reconcile_exchange, move, exchange_type):
        if move.upflow_commercial_partner_id:
            # create payment from bank statements
            # do not necessarily generate account.payment

            # At this point we expect customer to be already synchronized
            exchange = self._create_and_generate_upflow_exchange_record(
                move.commercial_partner_id.upflow_edi_backend_id
                or self._get_followup_backend(move),
                exchange_type,
                move,
            )
            reconcile_exchange.dependent_exchange_ids |= exchange
        else:
            raise UserError(
                _(
                    "You can reconcile journal items because the journal entry "
                    "%s (ID: %s) is not synchronisable with upflow.io, "
                    "because partner is not set but required."
                )
                % (
                    move.name,
                    move.id,
                )
            )

    def _is_customer_entry(self, reconcile):
        """Return true when all moves are linked to receivable lines"""
        return all(
            [
                acc_type.type == "receivable"
                for acc_type in reconcile.reconciled_line_ids.account_id.user_type_id
            ]
        )

    def on_record_create(self, account_full_reconcile, fields=None):
        if not self._is_customer_entry(account_full_reconcile):
            return
        first_move = account_full_reconcile.reconciled_line_ids.filtered(
            lambda move_line: move_line.move_id.commercial_partner_id
        )[0].move_id
        reconcile_exchange = self._create_and_generate_upflow_exchange_record(
            first_move.commercial_partner_id.upflow_edi_backend_id
            or self._get_followup_backend(first_move),
            "upflow_post_reconcile",
            account_full_reconcile,
        )
        if not reconcile_exchange:
            # in case no backend is returned there are nothing to do
            return
        for partial in account_full_reconcile.partial_reconcile_ids:
            self._ensure_related_move_is_synced(
                reconcile_exchange,
                partial.credit_move_id.move_id,
                "upflow_post_payments",
            )
            self._ensure_related_move_is_synced(
                reconcile_exchange, partial.debit_move_id.move_id, "upflow_post_refunds"
            )

    def on_record_unlink(self, account_full_reconcile):
        if account_full_reconcile.sent_to_upflow:
            # we are not using _create_and_generate_upflow_exchange_record
            # here because we want to generate payload synchronously
            # after wards record will be unlinked with no chance to retrieves
            # upflow_uuid
            first_move = account_full_reconcile.reconciled_line_ids.filtered(
                lambda move_line: move_line.move_id.commercial_partner_id
            )[0].move_id
            backend = (
                first_move.commercial_partner_id.upflow_edi_backend_id
                or self._get_followup_backend(first_move)
            )
            if backend:
                exchange_record = backend.create_record(
                    "upflow_post_reconcile",
                    self._get_exchange_record_vals(account_full_reconcile),
                )
                backend.with_context(unlinking_reconcile=True).exchange_generate(
                    exchange_record
                )
