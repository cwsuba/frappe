// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt 

// assign to is lined to todo
// refresh - load todos
// create - new todo
// delete to do

wn.provide("wn.ui.form");

wn.ui.form.AssignTo = Class.extend({
	init: function(opts) {
		$.extend(this, opts);
		var me = this;
		this.wrapper = $('<div>\
			<div class="alert-list" style="margin-bottom: 7px;"></div>\
		</div>').appendTo(this.parent);
		
		this.$list = this.wrapper.find(".alert-list");
		
		this.parent.find(".btn").click(function() {
			me.add();
		});
		this.refresh();
	},
	refresh: function() {
		if(this.frm.doc.__islocal) {
			this.parent.toggle(false);
			return;
		}
		this.parent.toggle(true);
		this.render(this.frm.get_docinfo().assignments);
	},
	render: function(d) {
		var me = this;
		this.frm.get_docinfo().assignments = d;
		this.$list.empty();
		if(this.dialog) {
			this.dialog.hide();			
		}

		if(d && d.length) {
			for(var i=0; i<d.length; i++) {	
				var info = wn.user_info(d[i]);
				info.owner = d[i];
				info.avatar = wn.avatar(d[i]);

				$(repl('<div class="alert alert-success" style="margin-bottom: 7px;">\
					%(avatar)s %(fullname)s \
					<a class="close" href="#" style="top: 1px;"\
						data-owner="%(owner)s">&times;</a></div>', info))
					.appendTo(this.$list);

				this.$list.find(".avatar").css("margin-top", "-7px")
				this.$list.find('.avatar img').centerImage();
			}

			// set remove
			this.$list.find('a.close').click(function() {
				wn.call({
					method:'webnotes.widgets.form.assign_to.remove', 
					args: {
						doctype: me.frm.doctype,
						name: me.frm.docname,
						assign_to: $(this).attr('data-owner')	
					}, 
					callback:function(r,rt) {
						me.render(r.message);
						me.frm.toolbar.show_infobar();
						me.frm.comments.refresh();
					}
				});
				return false;
			});
		} else {
			$('<p class="text-muted">' + wn._("No one") + '</p>').appendTo(this.$list);
		}
	},
	add: function() {
		var me = this;
		if(!me.dialog) {
			me.dialog = new wn.ui.Dialog({
				title: wn._('Add to To Do'),
				width: 350,
				fields: [
					{fieldtype:'Link', fieldname:'assign_to', options:'Profile', 
						label:wn._("Assign To"), 
						description:wn._("Add to To Do List of"), reqd:true},
					{fieldtype:'Data', fieldname:'description', label:wn._("Comment")}, 
					{fieldtype:'Date', fieldname:'date', label: wn._("Complete By")}, 
					{fieldtype:'Select', fieldname:'priority', label: wn._("Priority"),
						options:'Low\nMedium\nHigh', 'default':'Medium'},
					{fieldtype:'Check', fieldname:'notify', 
						label:wn._("Notify By Email"), "default":1},
					{fieldtype:'Check', fieldname:'restrict',
						label:wn._("Add This To User's Restrictions")
							+ ' <a class="assign-user-properties"><i class="icon-share"></i></a>'},
					{fieldtype:'Button', label:wn._("Add"), fieldname:'add_btn'}
				]
			});
						
			me.dialog.fields_dict.restrict.$wrapper
				.find(".assign-user-properties")
				.on("click", function() {
					wn.route_options = {
						property: me.frm.doctype,
						user: me.dialog.get_value("assign_to")
					};
					wn.set_route("user-properties");
				});
			
			me.dialog.fields_dict.add_btn.input.onclick = function() {
				
				var assign_to = me.dialog.fields_dict.assign_to.get_value();
				var args = me.dialog.get_values();
				if(assign_to) {
					return wn.call({
						method:'webnotes.widgets.form.assign_to.add', 
						args: $.extend(args, {
							doctype: me.frm.doctype,
							name: me.frm.docname,
							assign_to: assign_to
						}),
						callback: function(r,rt) {
							if(!r.exc) {
								me.render(r.message);
								me.frm.toolbar.show_infobar();
								me.frm.comments.refresh();
							}
						},
						btn: this
					});
				}
			}
			me.dialog.fields_dict.assign_to.get_query = "webnotes.core.doctype.profile.profile.profile_query";
		}
		me.dialog.clear();
		
		(function toggle_restrict() {
			var can_restrict = wn.model.can_restrict(me.frm.doctype, me.frm);
			me.dialog.fields_dict.restrict.$wrapper.toggle(can_restrict);
			me.dialog.get_input("restrict").prop("checked", can_restrict);
		})();
		
		if(me.frm.meta.title_field) {
			me.dialog.set_value("description", me.frm.doc[me.frm.meta.title_field])
		}
		
		me.dialog.show();
		
		if(!wn.perm.get_perm(me.frm.doctype)[0].restricted) {
			me.dialog.fields_dict.restrict.set_input(0);
			me.dialog.fields_dict.restrict.$wrapper.toggle(false);
		}
	}
});

