odoo.define('logistic_ecpay.print_cvs_shipping', function (require) {
    "use strict";
    // 註冊表物件
    // TODO 這裡要改寫成 owl component
    var widgetRegistry = require('web.widget_registry');
    var Widget = require('web.Widget');
    var FieldManagerMixin = require('web.FieldManagerMixin');

    var print_cvs_widget = Widget.extend(FieldManagerMixin, {
        template: 'logistic_ecpay.print_cvs_template',
        xmlDependencies: ['/logistic_ecpay/static/src/xml/print_cvs.xml'],
        events: {
            'click .o_print_cvs_button': '_on_button_clicked',
        },
        init: function (parent, node) {
            this.model_id = node.data.id;
            this._super(...arguments);
        },

        // 定義事件的 method
        _on_button_clicked: function () {
            console.log("_on_button_clicked");
            var deferred = new jQuery.Deferred()
            var self = this;
            var x = window.open('', '', 'width=800, height=600, resizeable, scrollbars');
            $(x.document.body).html("<p>請稍後, 正在重新導向中...</p>");
            this._rpc({
                model: 'shipping.ecpay.model',
                method: 'print_c2c_logistic',
                args: [self.model_id],
            }).then(function (result) {
                x.document.write(result);
                x.document.getElementById("ecpay_print").submit();
                deferred.resolve();
            });
            return jQuery.when(this, deferred);
        },
    });

    // widgetRegistry.add('print_cvs_shipping', print_cvs_widget);

});
