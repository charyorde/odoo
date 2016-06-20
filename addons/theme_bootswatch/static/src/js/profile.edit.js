odoo.define('gw.profileedit', function(require) {
  "use strict";
  var core = require('web.core');
  var Widget = require('web.Widget');

  var ProfileEdit = Widget.extend({
    template: 'ProfileEdit',
    init: function(parent) {
      // Constructor
      // Variables to set and data to load before DOM is read
      this.company_type = null
    },
    start: function() {
      var self = this; 
      this.company_type = $(ele).val()
      if (company_type == 'person') {
        self.renderFiles()
      }
    },
    renderFiles: function() {
    
    }
  })

})
