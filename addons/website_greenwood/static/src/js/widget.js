var instance = openerp;
var QWeb = instance.web.qweb;
instance.gw = {}

instance.gw.FieldInputFile = instance.web.form.AbstractField.extend({
  template: "GWProductPromoImage",
  start: function() {
    var self = this
    var model = new instance.web.Model("product.template");
    console.log("this.session", this.session)
    // query to get the filename
    var id = JSON.stringify(this.view.datarecord.id)
    $('input[name="gw_pid"]').val(id)
    this.filename = ''
    var uid = this.session.uid
    this.$ele = $('input#promo_image')
    this.$filenameEle = $('input[name="gw_promofn"]')
    this.fileattached = []
    
    model.call('get_product_promo_image', [id], {context: new instance.web.CompoundContext()}).then(function(result) {
      self.filename = result
      console.log("this.filename", self.filename)
      // retrieve the filename so that set_value and render_value can use it
      if (self.filename) {
        self.setValue(self.filename)
        self.showCount(self.filename)
      }
      if(self.view.get("actual_mode") == "view" && self.filename) {
        console.log('view mode')
        //self.$ele.attr('disabled', 'disabled')
        self.render_value()
      }

    })

    this.undisable = function() {
      console.log('undisable is called')
    }

    this.attachHandler = {
      change: function(e, data) {
        var $ele = $('input#promo_image')
        msg = $ele.attr('data-gw-files').replace('{count}', data.files.length)
        $ele.next().find('span').html(msg)
      },

      done: function(e, data) {
        console.log("self in fileupload done", self)
        var filename = data.files[0]['name']
        $('input[name="gw_promofn"]').val(data.files[0]['name'])
        console.log("gw_promofn value", $('input[name="gw_promofn"]').val())
        // save the file permanently
        path = '/gw/product/update'
        instance.session.rpc(path, {
          id: $('input[name="gw_pid"]').val(),
          filename: filename
        }, {})
        .then(function(res){ console.log('Model updated successfully', res) })
      },
    }
    this.$el.fileupload(this.attachHandler)
  },

  setValue: function(value_) {
    $('input[name="gw_promofn"]').val(value_)
    this.set_value(value_)
  },
  
  showCount: function(filename) {
    this.fileattached.push(filename)
    msg = this.$ele.attr('data-gw-files').replace('{count}', this.fileattached.length)
    this.$ele.next().find('span').html(msg)
  },

  render_value: function() {
    if (this.$filenameEle.val()) {
      this.setValue(this.$filenameEle.val())
   }
    console.log("render_value", this.get("value"))
    //this.$el.html(this.filename)
  }

})

instance.gw.FieldSwiftFile = instance.web.form.AbstractField.extend({
  template: "GWSwiftFile",
  start: function() {
    var self = this
    var model_field = self.name
    console.log("model_field", model_field)
    var model = new instance.web.Model("res.partner");
    console.log("this.session", this.session)
    var uid = this.session.uid
    var $ele = $('span#gw-dwnld-link a')
    ele = this.$el
    //model.call('_find_partner_by_userid', [uid], {context: new instance.web.CompoundContext()}).then(function(result) {
    //})
    model.query([model_field])
    .filter(['user_id', '=', uid])
    .first()
    .then(function(result) {
      console.log("model query result", result)
      var file = result[model_field]
      if (file) {
        fname = Object.keys(file)
        fpath = _.toArray(file)
        self.setValue([fname, fpath])
        //self.render_value()
      }
    })
  },

  setValue: function(value_) {
    this.$ele.attr('href', value_[1])
    this.$ele.html(value_[0])
    this.set_value(value_)
  },

  render_value: function() {
    console.log("render_value called auto")
  }

});

instance.gw.FieldSwiftFiles = instance.web.form.AbstractField.extend({
  template: "GWSwiftFiles",
  start: function() {
    var self = this
    field = this.$el
    var model = new instance.web.Model("res.partner");
    var uid = this.session.uid
    // query to get the filename
    var id = JSON.stringify(this.view.datarecord.id)
  }
})

instance.web.form.widgets.add('gwinputfile', 'instance.gw.FieldInputFile')
instance.web.form.widgets.add('gwswiftfile', 'instance.gw.FieldSwiftFile')
//instance.web.form.widgets.add('gwswiftfiles', 'instance.gw.FieldSwiftFiles')
