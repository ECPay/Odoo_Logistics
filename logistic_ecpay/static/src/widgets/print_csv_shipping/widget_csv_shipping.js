/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

export class PrintCSVShipping extends Component {
    async _printShipping(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        let record = this.props.record;

        if (!record.data.id) {
            return true;
        }

        window.open(
            `/web/logistic/print_csv_shipping/${record.data.id}`,
            '_blank',
            'noopener'
        );
    }
}


PrintCSVShipping.template = 'logistic_ecpay.PrintCSVShipping';

PrintCSVShipping.props = {
    ...standardWidgetProps,
};

registry.category("view_widgets").add("print_cvs_shipping", PrintCSVShipping);