// Commons to all gw modules
GW = {}

GW.ProfileCreate = function() {
  // @TODO On load, make sure swift is available before 
  // begining file upload
  this.$fileFields = $('.inputfile')
  this.$fns = $('#gw_idfn, #gw_tncyfn, #gw_pyslpfn')
  this.corp_fields = $('.corp')
  this.ind_fields = $('.ind')
  this.$spi = $('#spinner-identity')
  this.$spt = $('#spinner-tenancy')
  this.$spp = $('#spinner-payslips')
  this.$submit = $('button[type="submit"')
  this.$idstatus = $('#identity-status')
  this.$pysstatus = $('#payslips-status')
  this.$tncystatus = $('#tenancy-status')
  this.idattachList = []

  var self = this
  
  var $spi = $('#spinner-identity')
  var $spt = $('#spinner-tenancy')
  
  var $account_type = $('#account_type')
  var $ind_fields = $('div.ind')
  var $corp_fields = $('div.corp')
  var $checked = $("#account_type input:checked")
  var cv = $checked.attr('value')
  if (cv == 'person') {
    $corp_fields.hide()
  }
  else {
    $ind_fields.hide()
  }
  
  $account_type.find("input[value='person']").on('click', function(e) {
    $corp_fields.hide()
    $ind_fields.show()
  })
  $("#account_type input[value='company']").on('click', function(e) {
    $ind_fields.hide()
    $corp_fields.show()
  })

  this.$submit.click(function(ev) {
    //alert('clicked')
    ev.preventDefault(); // prevent submit until we validate
    ev.stopPropagation();
    if ($("#account_type input:checked").val() == 'company') {
      console.log('removed person fields')
      $ind_fields.find('input').each(function(i, ele) { $(ele).removeAttr('required')})
      $ind_fields.remove();
    }
    else if ($("#account_type input:checked") == 'person') {
      $corp_fields.remove();
      // If this.idfile.props('files').length is < 1, inform user to upload files
      // If this.tenancyfile.props('files').length is < 1, inform user to upload files
      // If this.payslipsfile.props('files').length is < 1, inform user to upload files
    }
    var $form = $(ev.currentTarget).parents('form');
  })
  
  var prepopulate = function(ele) {
    console.log("ele", ele)
    var file = $(ele).val().split(',')
    if ($(ele).attr('id') == 'gw_idfn') {
      setTimeout(function() {
        displayFile(file, '#identity-status ul')
        //msg = $('#identity_id').attr('data-gw-files').replace('{count}', file.length)
        //$('#identity_id').next().find('span').html(msg)
        setFileCount('#identity_id', file.length)
      }, 3000)
    }
    if ($(ele).attr('id') == 'gw_tncyfn') {
      displayFile(file, '#tenancy ul')
      setFileCount('#tenancy', file.length)
    }
    if ($(ele).attr('id') == 'gw_pyslpfn') {
      displayFile(file, '#payslips ul')
      setFileCount('#payslips', file.length)
    }
  };

  this.$fns.each(function(i, ele) {
    console.log('val', $(ele).val())
    if ($(ele).val()) {
      prepopulate(ele)
    }
  });

  this.idHandler = {
    change: function(e, data) {
      console.log('onchange')
      msg = $(this).attr('data-gw-files').replace('{count}', data.files.length)
      $(this).next().find('span').html(msg)
    },

    done: function(e, data) {
      $spi.hide('slow')
      displayFile([data.files[0]['name']], '#identity-status ul')
      console.log("input value", $(this).prop('files'))
      $('input[name="gw_idfn"]').val(data.files[0]['name'])
      console.log("gw_idfn value", $('input[name="gw_idfn"]').val())
    
    },

    always: function(e, data) {
      control($spi, data)
    },

    fail: function(e, data) {
      setStatus(self.$idstatus, data.textStatus, 'File attach failed. Please try again.', 5000)
    }
  };
  
  $('#identity_id').fileupload(this.idHandler)

  this.payslipsHandler = {
    dataType: 'json',
    singleFileUploads: false,
    done: function(e, data) {
      console.log('upload completed', data)
      var filenames = []
      $(data.files).each(function (index, file) {
        console.log("file", file)
        //displayFile(file.name, '#payslips-status ul')
        filenames.push(file.name)
      });
        displayFile(filenames, '#payslips-status ul')
      $('input[name="gw_pyslpfn"]').val(filenames.join(','))
    },
    fail: function(e, data) {
      setStatus(self.$pysstatus, data.textStatus, 'File attach failed. Please try again.', 5000)
    }
  }

  $('#payslips').fileupload(this.payslipsHandler)

  this.tenancyHandler = {
    dataType: 'json',
    done: function(e, data) {
      $spt.hide('slow')
      displayFile([data.files[0]['name']], '#tenancy-status ul')
      $('input[name="gw_tncyfn"]').val(data.files[0]['name'])
    },
    always: function(e, data) {
      control($spi, data)
    },
    fail: function(e, data) {
      setStatus(self.$tncystatus, data.textStatus, 'File attach failed. Please try again.', 5000)
    }
  }

  $('#tenancy').fileupload(this.tenancyHandler)


  var displayFile = function(file, ele) {
    file.forEach(function(f) {
      template = '<li>' + f + '</li>'
      $(ele).append(template)
    })
    $(ele).parent().fadeIn()
  }

  var control = function(spinner, data) {
    if (data.textStatus != 'success') {
      // continue spinning 
      spinner.show('slow')
    }
    if (data.textStatus == 'error') {
      spinner.delay(10000).fadeOut();
    }
  
  }

  var setStatus = function(ele, textstatus, message, timeout) {
    if (textstatus == 'error' ) {
      ele.append(message).show().delay(timeout).fadeOut();
    }
  
  }

  var setFileCount = function(ele, size) {
    msg = $(ele).attr('data-gw-files').replace('{count}', size)
    $(ele).next().find('span').html(msg)
  }

  var removeAttachedFile = function(file) {
  
  }

  var retrieveTempFile = function(file) {
    // Retrieve temp file if form hasn't been submitted or a failed submit
  }

  /**
    * @param ele array
    */ 
  var removeElement = function(ele) {
    // Loop through each ele and remove from dom
  }

  var validate = function(form) {
    alert('javascript validation called')
    return false
  }
}

GW.formValidate = function() {
  console.log('formValidate')
}

GW.Sale = function() {
  this.cart = $('table#cart_products')
  this.$order_total = $('table#cart_total th > h3')[1]
  this.$order_taxes_lbl = $('table#cart_total td')[0]
  this.$order_taxes = $('table#cart_total td')[1]
  this.acquirer_id = $('.oe_sale_acquirer_button[data-id]').val()
  
  var self = this

  if(this.cart.length > 0) {
    $('.rightSidebar .sidebar-body p').html(this.$order_taxes_lbl.innerHTML + this.$order_taxes.innerHTML)
    $('.rightSidebar .sidebar-footer span').html(this.$order_total.innerHTML)
  }
  
  //$('#gw-payment .a-submit').off('click').on('click', function () {
    // Make an rpc call
    // This rpc endpoint should change based on the acquirer_id
    //openerp.jsonRpc("/shop/payment/transaction/" + self.acquirer_id, 'call', {})
    //.then(function(res) {
      // If all is not well, set error message, return false
    //})
    //$(this).closest('form').submit();
  //});
}

$(document).ready(function() {
  new GW.ProfileCreate()
  new GW.Sale()
})
