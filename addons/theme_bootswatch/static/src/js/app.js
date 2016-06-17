odoo.define('website_greenwood.account', function(require) {
  // Commons to all gw modules
  var core = require('web.core');

  var profile = {
    
    edit: function() {
    
    },

    displayFile: function(file, ele) {
      template = '<b>' + file + '</b>'
      $(ele).append(template).show('slow')
    }
  }

  function ProfileCreate() {
    
    
  }

  var fileUploadHandler = function() {
    console.log('fileUploadHandler')
    var $spinner = $('#spinner-identity')
    $('#identity_id').fileupload({
      dataType: 'json',
     done: function(e, data) {
        console.log('upload completed', data)
        $spinner.hide('slow')
        // replace this input with a thumbnail of the image
        profile.displayFile(data.files[0]['name'], '#identity-status')
      
      },
      always: function(e, data) {
        if (data.textStatus != 'success') {
          // continue spinning 
          $spinner.show('slow')
        }
        if (data.textStatus == 'error') {
          $spinner.delay(10000).fadeOut();
        }
      },
      fail: function(e, data) {
        console.log(data)
        if (data.textStatus == 'error' ) {
          $("#identity-status").append('File attach failed. Please try again.').show().delay(5000).fadeOut();
        }
      }
    })

    $('#tenancy').fileupload({
    
    })

  }

  var filesUploadHandler = function() {
    $('#payslips').fileupload({
      dataType: 'json',
      singleFileUploads: false,
      done: function(e, data) {
        console.log('upload completed', data)
        $(data.files).each(function (index, file) {
          console.log("file", file)
          profile.displayFile(file.name, '#payslips-status')
        });
      
      },
      fail: function(e, data) {
        console.log("Failed debug", data)

      }
    
    })
  
  }

  $(document).ready(function() {

    fileUploadHandler();
    filesUploadHandler();

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

      // @todo exclude or disable all individual form fields when we're in corp view
      
    })

    $('div.oe_login_buttons > button[type="submit"]').on('click', function() {

      if ($("#account_type input:checked").val() == 'company') {
        console.log('removed person fields')
        $ind_fields.find('input').each(function(i, ele) { $(ele).removeAttr('required')})
        $ind_fields.remove();
      }
      else if ($("#account_type input:checked") == 'person') {
        $corp_fields.remove();
      }
      
    })
  })

})
