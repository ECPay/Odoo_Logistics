'use strict';
odoo.define('logistic_ecpay.checkout', function (require) {
  // 建立環境-變數
  var ajax = require('web.ajax');
  var show_cvs_url = '/shipping/map/';
  var iframe_link = '';
  var check_name = false, check_mobile = false, check_address = false, check_store = false;
  // 建立環境-函數陳述式
  function show_cvs_map() {
    // 開啟一個新視窗
    var win = window.open(iframe_link, 'CVS map', config = 'width=1024,height=600,status=no,scrollbars=yes,toolbar=no,location=no,menubar=no');
    // 偵測是否關掉視窗, 關掉後會發 ajax 給 server 請求 store info
    var timer = setInterval(function () {
      if (win.closed) {
        clearInterval(timer);
        ajax.jsonRpc('/shipping/update_carrier', 'call', {})
          .then(function (data) {
            if (data['CVSStoreID'] || data['CVSStoreName'] || data['CVSTelephone'] || data['CVSAddress']) {
              $('#CVSStoreID').val(data['CVSStoreID']);
              $('#CVSStoreName').val(data['CVSStoreName']);
              $('#CVSTelephone').val(data['CVSTelephone']);
              $('#CVSAddress').val(data['CVSAddress']);
              $('.ecpaylogistic-warning').hide();
              check_store = true;
            } else {
              $('.ecpaylogistic-warning').show();
              check_store = false;
            }
          });
      }
    }, 1000);
  }

  $(window).on("load", function () {

    let isPublish = document.getElementById("isPublish");

    if (isPublish != null && isPublish.innerText === 'True') {
      // 隱藏 Add an address 的按鈕 以及 Shipping Address 的 panel
      $('div.row.all_shipping').hide();

      var submit_botton = $('.btn.btn-primary.pull-right.mb32')
      var check_warning = function () {
        if (check_name) {
          $('#warning-ReceiverName').hide();
        } else {
          $('#warning-ReceiverName').show();
        }
        if (check_mobile) {
          $('#warning-ReceiverCellPhone').hide();
        } else {
          $('#warning-ReceiverCellPhone').show();
        }
        if (check_address) {
          $('#warning-ReceiverAddress').hide();
        } else {
          $('#warning-ReceiverAddress').show();
        }
      }

      var submit_botton_validate = function () {
        if (($('#shipping_method').val() === "FAMI") ||
          ($('#shipping_method').val() === "UNIMART") ||
          ($('#shipping_method').val() === "HILIFE")) {
          if (check_name && check_mobile && check_store) {
            submit_botton.prop('disabled', false);
          } else {
            submit_botton.prop('disabled', true);
          }
        } else {
          if (check_name && check_mobile && check_address) {
            submit_botton.prop('disabled', false);
          } else {
            submit_botton.prop('disabled', true);
          }
        }
        check_warning();
      }

      // Confirm button disable
      submit_botton.prop('disabled', true);
      // 便利商店資訊
      $('#ecpaylogistic-store-info').hide();
      // 收件人地址
      $('#ecpay_loistic_receiver_address').hide();
      // 收件人姓名警告
      $('#warning-ReceiverName').hide();
      // 收件人手機警告
      $('#warning-ReceiverCellPhone').hide();
      // 收件人地址警告
      $('#warning-ReceiverAddress').hide();

      // 當動作觸發時(選擇物流方式)
      $('#logistic_selection').on("change", "#shipping_method", function () {
        // 設定初始值
        $('.ecpaylogistic_stname').html('');
        $('.ecpaylogistic_staddr').html('');
        $('.ecpaylogistic_sttel').html('');
        if (($('#shipping_method').val() === "FAMI") ||
          ($('#shipping_method').val() === "UNIMART") ||
          ($('#shipping_method').val() === "HILIFE")) {
          $('#ecpaylogistic-store-info').fadeIn();
          $('#ecpay_loistic_receiver_address').fadeOut();
          iframe_link = show_cvs_url + $('#shipping_method').val();
          show_cvs_map();
        } else {
          $('#ecpay_loistic_receiver_address').fadeIn();
          $('#ecpaylogistic-store-info').fadeOut();
        }
        var payment_type = $('option:selected', this).attr('value');
        $('#shipping_type').val(payment_type);
        // 檢查各欄位所需要的資訊是否有填寫
        submit_botton_validate();
      });

      let check_name_length = (name) => {
        let l = name.length;
        let blen = 0;
        for (let i = 0; i < l; i++) {
          if ((name.charCodeAt(i) & 0xff00) != 0) {
            blen++;
          }
          blen++;
        }
        return blen;
      }

      // 1. 字元限制為為 4~10 字元(中文 2~5 個字, 英文 4~10 個字)
      // 2. 不可有符號^ ' ` ! ＠ # % & * + \ " < > | _ [ ]
      // 3. 不可有空白 , 及，若帶有空白, 及，系統自動去除。
      // 檢查姓名是否輸入
      $('#ReceiverName').on('input', function () {
        var input = $(this);
        var is_name = input.val();
        var format = /[ !@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/;
        let format_number = /[0-9]/;
        if (is_name && check_name_length(is_name) >= 4 && check_name_length(is_name) <= 10 &&
          (format.test(is_name) === false) && (format_number.test(is_name) === false)) {
          $('#div-ReceiverName').removeClass("has-error");
          check_name = true;
        } else {
          $('#div-ReceiverName').addClass("has-error");
          check_name = false;
        }
        submit_botton_validate();
      });

      // 檢查是否輸入手機號碼
      $('#ReceiverCellPhone').on('input', function () {
        var input = $(this);
        var re = /^[09]{2}[0-9]{8}$/;
        var is_mobile = re.test(input.val());
        if (is_mobile) {
          $('#div-ReceiverCellPhone').removeClass("has-error");
          check_mobile = true;
        } else {
          $('#div-ReceiverCellPhone').addClass("has-error");
          check_mobile = false;
        }
        submit_botton_validate();
      });

      // 檢查是否輸入地址
      $('#ReceiverAddress').on('input', function () {
        var input = $(this);
        var is_address = input.val();
        var zipcode = $('#twzipcode').twzipcode('get', 'zipcode');
        if (is_address && is_address.length >= 6 && is_address.length <= 60 && (zipcode != false)) {
          $('#div-ReceiverAddress').removeClass("has-error");
          check_address = true;
        } else {
          $('#div-ReceiverAddress').addClass("has-error");
          check_address = false;
        }
        submit_botton_validate();
      });
    } else {
      $('#logistic_ecpay_form').hide();
    }
  });
  $(window).on("load", function () {
    if ($("#delivery_method").length) {
      let ecpay_label;
      let ecpay_warning = "ECPay 單筆運送金額上限為 20000 元，請選擇其他交貨方式或減少訂購商品"
      let check_delivery = ()=>{
        let delivery_method = $("#delivery_method");
        let labels = delivery_method.find('label');
        for (let i=0; i<labels.length; i++) {
          if ((labels[i].control.checked === true) &&
          (labels[i].innerText.includes('ECPay'))) {
            ecpay_label = labels[i];
            return true;
          }
        }
        return false;
      }
      let check_currency = ()=>{
        let order_total = $('#order_total');
        let currency_element = order_total.find('span.oe_currency_value');
        let currency = parseInt(currency_element[0].innerText.replace(/,/g, ""));
        if (currency > 20000) {
          return true;
        } else {
          return false;
        }
      }
      let hide_ecpay_cod = (hide=true)=>{
        let payment_method = $("#payment_method");
        let inputs = payment_method.find('label > input[type="radio"]');
        for (let i=0; i<inputs.length; i++) {
          if ($(inputs[i]).data('provider') === 'transfer') {
            let payment_name = inputs[i];
            if (payment_name.nextElementSibling.
              innerText.includes('ECPay')) {
              payment_name.checked = false;
              if (hide) {
                $(payment_name).parents('.panel-body').hide();
              } else {
                $(payment_name).parents('.panel-body').show();
              }
            }
          }
        }
      }
      let run_ecpay_delivery_action = ()=>{
        setTimeout(()=>{
          if (check_delivery() && check_currency()) {
            $('button#o_payment_form_pay').attr('disabled', true);
            $(ecpay_label).text(ecpay_warning);
          } else {
            $('button#o_payment_form_pay').attr('disabled', false);
            $(ecpay_label).text("ECPay");
          }
          if (check_delivery() === false) {
            hide_ecpay_cod();
          } else {
            hide_ecpay_cod(false);
          }
        }, 1000);
      }
      run_ecpay_delivery_action();
      $(document).ready(run_ecpay_delivery_action);
      $('#delivery_method').click(run_ecpay_delivery_action);
    }
  });
});