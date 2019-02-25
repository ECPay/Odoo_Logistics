odoo.define('logistic_ecpay.print_cvs_shipping', function (require) {
  "use strict";
  // 註冊表物件
  var widgetRegistry = require('web.widget_registry');
  var Widget = require('web.Widget');
  var FieldManagerMixin = require('web.FieldManagerMixin');

  var print_cvs_widget = Widget.extend(FieldManagerMixin, {
    template: 'print_cvs_template',
    events: {
      'click .o_print_cvs_button': '_on_button_clicked',
    },
    init: function (parent, node) {
      this.MerchantTradeNo = node.data.MerchantTradeNo;
      this._super(parent, node);
      FieldManagerMixin.init.call(this);
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
        args: [self.MerchantTradeNo],
      }).then(function (result) {
        x.document.write(result);
        x.document.getElementById("ecpay_print").submit();
        deferred.resolve();
      });
      return jQuery.when(this, deferred);
    },
  });

  widgetRegistry.add('print_cvs_shipping', print_cvs_widget);

});
