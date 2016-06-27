odoo.define('gw.profilecreate', function(require) {

  var core = require('web.core');
  var Widget = require('web.Widget');

  var ProfileCreate = Widget.extend({
    template: 'ProfileCreate',
    init: function(parent) {
      console.log('Initialized gw.profilecreate')
    }
  })
  /*function ProfileCreate() {
  
  }

  $(document).ready(function() {
  
    ProfileCreate()
  })*/
})
