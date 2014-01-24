# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt 

from __future__ import unicode_literals
"""assign/unassign to ToDo"""

import webnotes
from webnotes import _
from webnotes.utils import cint
from webnotes.widgets.form.load import get_docinfo

def get(args=None):
	"""get assigned to"""
	if not args:
		args = webnotes.local.form_dict
		
	get_docinfo(args.get("doctype"), args.get("name"))
	
	return webnotes.conn.sql_list("""select owner from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
		order by modified desc limit 5""", args)
		
@webnotes.whitelist()
def add(args=None):
	"""add in someone's to do list"""
	if not args:
		args = webnotes.local.form_dict
		
	if webnotes.conn.sql("""select owner from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
		and owner=%(assign_to)s""", args):
		webnotes.msgprint("Already in todo", raise_exception=True)
		return
	else:
		from webnotes.utils import nowdate
		
		d = webnotes.bean({
			"doctype":"ToDo",
			"owner": args['assign_to'],
			"reference_type": args['doctype'],
			"reference_name": args['name'],
			"description": args.get('description'),
			"priority": args.get("priority", "Medium"),
			"status": "Open",
			"date": args.get('date', nowdate()),
			"assigned_by": args.get('assigned_by', webnotes.user.name),
		}).insert(ignore_permissions=True).doc
		
		# set assigned_to if field exists
		from webnotes.model.meta import has_field
		if has_field(args['doctype'], "assigned_to"):
			webnotes.conn.set_value(args['doctype'], args['name'], "assigned_to", args['assign_to'])
			
	try:
		if cint(args.get("restrict")):
			from webnotes.core.page.user_properties import user_properties
			user_properties.add(args['assign_to'], args['doctype'], args['name'])
			webnotes.msgprint(_("Restriction added"))
	except webnotes.PermissionError:
		webnotes.throw("{cannot}: {user}, {_for}: {doctype} {_and}: {name}".format(cannot=_("You cannot restrict User"), 
			user=args['assign_to'], _for=_("for DocType"), doctype=_(args['doctype']), _and=_("and Name"),
			name=args['name']))

	# notify
	if not args.get("no_notification"):
		notify_assignment(d.assigned_by, d.owner, d.reference_type, d.reference_name, action='ASSIGN', description=args.get("description"), notify=args.get('notify'))
		
	# update feeed
	try:
		from erpnext.home import make_feed
		from webnotes.utils import get_fullname
		make_feed('Assignment', d.reference_type, d.reference_name, webnotes.session['user'],
			'[%s] Assigned to %s' % (d.priority, get_fullname(d.owner)), '#C78F58')
	except ImportError, e:
		pass
		
	return get(args)

@webnotes.whitelist()
def remove(doctype, name, assign_to):
	"""remove from todo"""
	todo = webnotes.bean("ToDo", {"reference_type":doctype, "reference_name":name, "owner":assign_to, "status":"Open"})
	todo.doc.status = "Closed"
	todo.save(ignore_permissions=True)
		
	# clear assigned_to if field exists
	from webnotes.model.meta import has_field
	if has_field(doctype, "assigned_to"):
		webnotes.conn.set_value(doctype, name, "assigned_to", None)

	notify_assignment(todo.doc.assigned_by, todo.doc.owner, todo.doc.reference_type, todo.doc.reference_name)

	return get({"doctype": doctype, "name": name})
	
def clear(doctype, name):
	for assign_to in webnotes.conn.sql_list("""select owner from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s""", locals()):
			remove(doctype, name, assign_to)

def notify_assignment(assigned_by, owner, doc_type, doc_name, action='CLOSE', 
	description=None, notify=0):
	"""
		Notify assignee that there is a change in assignment
	"""	
	if not (assigned_by and owner and doc_type and doc_name): return

	# self assignment / closing - no message
	if assigned_by==owner:
		return

	from webnotes.boot import get_fullnames
	user_info = get_fullnames()

	# Search for email address in description -- i.e. assignee
	from webnotes.utils import get_url_to_form
	assignment = get_url_to_form(doc_type, doc_name, label="%s: %s" % (doc_type, doc_name))
		
	if action=='CLOSE':
		if owner == webnotes.session.get('user'):
			arg = {
				'contact': assigned_by,
				'txt': "The task %s, that you assigned to %s, has been \
					closed." % (assignment,
						user_info.get(owner, {}).get('fullname'))
			}
		else:
			arg = {
				'contact': assigned_by,
				'txt': "The task %s, that you assigned to %s, \
					has been closed	by %s." % (assignment,
					user_info.get(owner, {}).get('fullname'),
					user_info.get(webnotes.session.get('user'),
						{}).get('fullname'))
			}
	else:
		arg = {
			'contact': owner,
			'txt': "A new task, %s, has been assigned to you by %s. %s" \
				% (assignment,
				user_info.get(webnotes.session.get('user'), {}).get('fullname'),
				description and ("<p>Description: " + description + "</p>") or ""),
			'notify': notify
		}
		
	arg["parenttype"] = "Assignment"
	from webnotes.core.page.messages import messages
	import json
	messages.post(json.dumps(arg))
