# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class BaseUpflowEventListner(Component):

    _name = "base.upflow.event.listener"
    _inherit = "base.event.listener"

    def _get_followup_backend(self, record):
        return record.company_id.upflow_backend_id

    def _get_exchange_record_vals(self, record):
        return {
            "model": record._name,
            "res_id": record.id,
        }

    def _create_and_generate_upflow_exchange_record(
        self, backend, exchange_type, record
    ):
        if backend:
            exchange_record = backend.create_record(
                exchange_type, self._get_exchange_record_vals(record)
            )
            backend.with_delay().exchange_generate(exchange_record)
        else:
            return self.env["edi.exchange.record"]
        return exchange_record
