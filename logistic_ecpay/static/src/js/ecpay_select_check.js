odoo.define('logistic_ecpay.payment_delivery_shipping_ecpay_delivery_carrier', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    publicWidget.registry.WebsiteSaleDeliveryECPAY = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'change input[name="delivery_type"]': '_onDeliveryTypeChange',
            'click .js_ecpay_button': '_onECPAYButtonClick',
        },

        /**
         * @override
         */
        start: function () {
            this.$ecpayButton = this.$('.js_ecpay_button').attr('disabled', false).text('選擇物流方式');
            return this._super.apply(this, arguments);
        },

        /**
         * @private
         */
        _onDeliveryTypeChange: function (event) {
            let deliveryType = $(event.currentTarget).val();

            this.$ecpayButton[deliveryType === 'ECPay' ? 'show': 'hide']();
        },

        /**
         * @private
         */
        _onECPAYButtonClick: function (ev) {
            const self = this;
            ev.preventDefault();
            self.$ecpayButton.attr('disabled', true).text('跳轉選擇畫面中，請稍候');

            let sale_order_id = this.$el.find('input[name="sale_order_id"]').val();
            let delivery_carrier_id = this.$el.find('input[name="delivery_type"]:checked').val();
            ajax.jsonRpc('/shipping/create_temp_order', 'call', {
                sale_order_id,
                delivery_carrier_id,
            }).then(function (response) {
                if (response.success) {
                    document.write(JSON.parse(response.content));
                } else {
                    self.$ecpayButton.attr('disabled', false).text('選擇物流方式');
                    console.error(response.error);
                }
            }).catch(() => {
                self.$ecpayButton.text('發生了一些錯誤，請稍後重試');
                setTimeout(() => {
                    self.$ecpayButton.attr('disabled', false).text('選擇物流方式');
                }, 5000);
            });
        }

    });

    return publicWidget.registry.WebsiteSaleDeliveryECPAY;
});
