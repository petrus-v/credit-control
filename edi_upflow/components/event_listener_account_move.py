# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class AccountMoveUpflowEventListener(Component):
    """Intent of this class is to listen interesting account.move events

    used to create usefull exchange record for followup external system
    with upflow.io in mind (not sure it can be as generic)
    """

    _name = "account.move.upflow.event.listener"
    _inherit = "base.upflow.event.listener"
    _apply_on = ["account.move"]

    def on_post_account_move(self, moves):
        for move in moves:
            exchange_type = None
            pdf_exchange = None
            if move.move_type == "out_invoice":
                exchange_type = "upflow_post_invoice"
                pdf_exchange = "upflow_post_invoice_pdf"
            elif move.move_type == "out_refund":
                exchange_type = "upflow_post_credit_notes"
                pdf_exchange = "upflow_post_credit_notes_pdf"
            elif move.move_type == "entry" and move.payment_id:
                if (
                    move.payment_id.payment_type == "inbound"
                    and move.payment_id.partner_type == "customer"
                ):
                    exchange_type = "upflow_post_payments"
                elif (
                    move.payment_id.payment_type == "outbound"
                    and move.payment_id.partner_type == "customer"
                ):
                    exchange_type = "upflow_post_refunds"

            if not exchange_type:
                continue
            customer_exchange = self.env["edi.exchange.record"]
            backend = move.commercial_partner_id.upflow_edi_backend_id
            if not move.commercial_partner_id.upflow_uuid or not backend:
                backend = self._get_followup_backend(move)
                customer_exchange = self._create_and_generate_upflow_exchange_record(
                    backend, "upflow_post_customers", move.commercial_partner_id
                )
                move.commercial_partner_id.upflow_edi_backend_id = backend
            account_move_exchange = self._create_and_generate_upflow_exchange_record(
                backend, exchange_type, move
            )
            if not account_move_exchange:
                # empty recordset could be return in case no backend found
                continue
            account_move_exchange.dependent_exchange_ids |= customer_exchange
            if pdf_exchange:
                pdf_exchange = self._create_and_generate_upflow_exchange_record(
                    backend, pdf_exchange, move
                )
                pdf_exchange.dependent_exchange_ids |= account_move_exchange
