var data = {};
var app = [];
var group = [];
//$.post("/scheduler", "{\"a\":\"allEnv\"}", function (ret) {
//    data = ret
//})

$.ajax({
    url: "/scheduler",
    async: false,
    type: "POST",
    data: "{\"a\":\"allEnv\"}",
    success: function (ret) {
        data = ret;
    },
    dataType:"json"
});
// 初始化app
for(var da in data){
  if (app.indexOf(data[da].app) <= -1) {
    app.push(data[da].app);
  }
}
//group 清空 再插入

initGroup = function(app){
  var option = $(vm2.$el).children('select').children('option')[0];
  $(vm2.$el).children('select').children('option').remove();
  $(vm2.$el).children('select').append(option);
  group = [];
  for(var da in data){
      if (data[da].app == app) {
         group.push(data[da].group)
      }
  }
  vm2.options=group
}
Vue.component('select2', {
  props: ['options', 'value'],
  template: '#select2-template',
  mounted: function () {
    var vm = this
    // 给每个select2 ID 赋值 和v-model
    this.$el.id=this.$parent.$options.id;
    $(this.$el)
      // init select2
      .select2({ data: this.options })
      .val(this.value)
      .trigger('change')
      // emit event on change.
      .on('change', function () {
        vm.$emit('input', this.value)
        if(this.$parent.$options.id=='app'){
           initGroup(this.value);
        }
      })
  },
  watch: {
    value: function (value) {
      // update value
      $(this.$el).val(value).trigger('change');
    },
    options: function (options) {
      // update options
      $(this.$el).select2({ data: options })
    }
  },
  destroyed: function () {
    $(this.$el).off().select2('destroy')
  }
})

var vm1 = new Vue({
  id: 'app',
  el: '#envApp',
  template: '#demo-template',
  data: {
    options: app
  }
});

var vm2 = new Vue({
  id: 'group',
  el: '#envGroup',
  template: '#demo-template',
  data: {
    options:group
  }
});