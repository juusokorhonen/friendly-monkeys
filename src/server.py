#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
from sqlite3 import dbapi2 as sqlite3
from sqlite3 import IntegrityError
from flask import Flask, render_template, url_for, g, request, session, redirect, abort, flash, escape, make_response
from contextlib import closing
from flask_wtf import Form
from wtforms import TextField, validators, HiddenField
from math import ceil, floor
from random import randint, sample

# Define WTForms classes
class AddMonkeyForm(Form):
    """Form that adds a single monkey to the database."""
    username = TextField('Username', [validators.Length(min=4, max=25, message='Username should be 4...25 characters long')])
    name = TextField('Full name', [validators.InputRequired(message='Full name cannot be empty')])

class EditMonkeyForm(AddMonkeyForm):
	"""Form for editing a monkey in the database."""
	uid = HiddenField('ID#', [validators.NumberRange(min=0, message='ID mismatch')])

# Create application
app = Flask(__name__)

# Application configuration
app.config.update(dict(
    DATABASE = '/tmp/monkeys.db',
    DEBUG = True,
    SECRET_KEY = 'Amonkeystandinonitshead',
))
app.config.from_envvar('MONKEY_SETTINGS', silent=True)

# Database functions
def connect_db():
    """Connects to the database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

# Initialize database 
def init_db():
    """Creates tables to the database."""
    with closing(connect_db()) as db:
	with app.open_resource('schema.sql', mode='r') as f:
        	db.cursor().executescript(f.read())
	db.commit()	

# Returns the database connection
def get_db():
    """Returns the database connection and opens it whenever needed."""	
    db = getattr(g, 'db', None)
    if db is None:
	db = g.db = connect_db()
    return db	

# Query the database
def query_db(query, args=(), one=False):
    """Makes a query to the database and returns the results."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_request
def teardown_request(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
	


# Define routes

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/list')
def list():
	"""List monkeys from the database."""
	# Get list parameters
	#for arg in request.args:
	#		print(arg),
	#		print(" " + request.args.get(arg))
	lim = int(request.args.get('limit', 10))
	if (lim < 1):
		lim = 1 # Fall back to smallest possible limit
	off = int(request.args.get('offset', 0))
	if (off < 0):
		off = 0 # Fall back to 0 offset
	orderby = request.args.get('orderby', 'id')
	if (orderby not in ['id', 'username', 'name']):
		orderby = 'id' # Fall back to id, if value is strange
	order = request.args.get('order', 'asc')
	if (order not in ['asc', 'desc']):
		order = 'asc' # Fall back to ascending order
	# Make the database query
	numresults = query_db('SELECT COUNT(id) AS entries FROM monkeys', one=True)
	if (numresults['entries'] == 0):
		# No monkeys were returned
		return render_template('list_monkeys.html')
	else:
		# There are monkeys
		result = query_db('SELECT id,username,name FROM monkeys ORDER BY {orderby} {order} LIMIT ? OFFSET ?'.format(orderby=orderby, order=order), [lim, off])
		pages = int(ceil(numresults['entries']/float(lim)))
		thispage = int(floor(off/float(lim)))
		params = dict(limit=lim, offset=off, orderby=orderby, order=order, entries=numresults['entries'], pages=pages, pagenum=thispage)
		return render_template('list_monkeys.html', monkeys=result, params=params)

@app.route('/show/<username>')
def show(username):
    """Show the monkey profile, which is identified by username."""
    monkey = query_db('SELECT id,username,name FROM monkeys WHERE username=?', args=[username], one=True)

    #print(result)
    if (len(monkey) == 0):
        # Monkey search failed, so give 404
        abort(404)
        #return make_response(render_template('filenotfound.html'), 404)

    # Find friendships initiated by this monkey
    fs_init = query_db('SELECT id2 FROM friendships WHERE id1=?', args=[result['id']])
    num_init = len(fs_init)
    # Find friendships received by this monkey
    fs_rec = query_db('SELECT id1 FROM friendships WHERE id2=?', args=[result['id']])
    num_rec = len(fs_rec)
    # Parse these into lists
    fs_init_list = [x['id2'] for x in fs_init]
    fs_rec_list  = [x['id1'] for x in fs_rec]
    fs_list = list(set(fs_init_list.extend(fs_rec_list)))
    # Check for accepted/active friendships
    fs_active_list = [x for x in fs_init_list if x in fs_rec_list]
    num_active = len(fs_active_list)
    # List of initiated, but not accepted friendships
    fs_init_not_accepted_list = [x for x in fs_init_list if x not in fs_active_list]
    num_init_not_accepted = len(fs_init_not_accepted_list)
    # List of received, but not accepted friendships
    fs_rec_not_accepted_list = [x for x in fs_rec_list if x not in fs_active_list]
    num_rec_not_accepted = len(fs_rec_not_accepted_list)
    # Put these into tuples
    fs = (fs_active_list, fs_init_not_accepted_list, fs_rec_not_accepted_list)
    numfs = (num_active, num_init_not_accepted, num_rec_not_accepted)

    # Find the names for the friend-monkeys
    fr_names = query_db('SELECT id,username,name FROM monkeys WHERE id in (?)', args=[fs_list])

    return render_template('show_monkey.html', monkey=monkey, fs=fs, numfs=numfs, fr_names=fr_names)

@app.route('/edit/<uid>', methods=['GET', 'POST'])
def edit(uid):
	"""Shows the edit form and edits a monkey in the database."""
	form = EditMonkeyForm(request.form, uid=uid)
	# Results are in, so continue
	if (request.method == 'GET'):
		result = query_db('SELECT id,username,name FROM monkeys WHERE id=?', args=[uid], one=True)
		if (result is None):
			# Monkey search failed, so give 404
			abort(404)
		# Display the edit form
		return render_template('edit_monkey.html', form=form, monkey=result)
	elif (request.method == 'POST' and form.validate()):
		# Form was submitted and validated
		username = form.username.data
		name = form.name.data
		uid = form.uid.data
		form.uid = uid
		print("{}, {}, {}".format(username, name, uid))
		try:
			query_db('UPDATE monkeys SET username=?,name=? WHERE id=?', (username, name, uid), one=True)
                        get_db().commit()
		except: 
			msg = 'Updating monkey failed.' 
			flash(msg, 'error')
		else:
			# Make a note on the next page
			msg = 'Successfully updated monkey with username "{username}.'.format(username=escape(username))
			flash(msg)
                # Now refresh the monkey (this could be avoided, yet it's easier this way)
                result = query_db('SELECT id,username,name FROM monkeys WHERE id=?', args=[uid], one=True)
                if (len(result) == 0):
                        abort(404)
                return render_template('edit_monkey.html', form=form, monkey=result)
	else:
		# Something went wrong (form did not validate)
		result = query_db('SELECT id,username,name FROM monkeys WHERE id=?', args=[uid], one=True)
		if (len(result) == 0):
			abort(404)
		flash("Errors in form, please correct.", 'error')
		return render_template('edit_monkey.html', form=form, monkey=result)

@app.route('/add', methods=['GET', 'POST'])
def add():
    form = AddMonkeyForm(request.form)
    if (request.method == 'GET'):
        # Display the input form
        return render_template('add_monkey.html', form=form)
    elif (request.method == 'POST' and form.validate()):
        # Form has been sent and validated
        username = form.username.data
        name = form.name.data
        msg = "" # Message for next page flash
        # !!! Using prepared statements here, yet the safety should be checked
        try:
            query_db('INSERT INTO monkeys (username, name) VALUES (?, ?)', (username, name), one=True)
        except IntegrityError as e:
            msg += 'Adding monkey failed. Username "{username}" already in use.'.format(username=escape(username))
            flash(msg, 'error')
        else:
            get_db().commit() # Commit changes
            # Make a note on the next page
            msg = 'Successfully added a monkey named "{name}", with username "{username}".<br />\n<a href="{entryurl}" class="alert-link">See entry</a>.'.format(name=escape(name), username=escape(username), entryurl=url_for('show', username=username))
            #print(msg)
            flash(msg)
        return render_template('add_monkey.html', form=form) 
    else: # request method is post, yet the form did not validate
        errormsg = 'Adding monkey failed.'
        # Append error messages to flash
        if (form.errors):
            for field_name, field_errors in form.errors.items():
                for error in field_errors:
                    errormsg += '<br />{error}.\n'.format(error=error)
        flash(errormsg, 'error')
        return render_template('add_monkey.html', form=form)

@app.route('/delete/<uid>')
def delete(uid):
    confirm = int(request.args.get('confirm', 0))
    if (uid is None):
        abort(404)
    if (confirm == 1):
        try:
            result = query_db('SELECT id,name,username FROM monkeys WHERE id=?', [uid], one=True)
            if (result is None):
                raise IntegrityError()
            query_db('DELETE FROM monkeys WHERE id=?', [uid])
            get_db().commit()
        except IntegrityError as e:
            return render_template('delete_monkey.html', confirm=True, success=False, monkey=result)
        else:
            return render_template('delete_monkey.html', confirm=True, success=True, monkey=result)
    else:
        result = query_db('SELECT id,name,username FROM monkeys WHERE id=?', [uid], one=True)
        #print(result)
        if (len(result) == 0):
            abort(404)
        return render_template('delete_monkey.html', confirm=False, monkey=result, uid=uid)
        

# Make example data into the database
@app.route('/load_example_data/')
def load_example_data():
	confirm = int(request.args.get('confirm', 0))
	if (confirm == 1):
		if (insert_example_data()):	
			# Success
			return render_template('load_example_data.html', confirm=True, success=True)
		else:
			# Failed
			return render_template('load_example_data.html', confirm=True, success=False)
	else:
		# Show confirm dialog
		return render_template('load_example_data.html', confirm=False)

def insert_example_data():
	values = [('rlemur', 'Ringo the Lemur'), 
		('macaq11', 'Madison Macaque'), 
		('ggorilla', 'Gonzo Gorilla'), 
		('ltamarin', 'Lionel Tamarin'), 
		('indira', 'Dira Indri'),
		('patas', 'Patas Monkey'),
		('pansy', 'Pansy the Chimpanzee'),
		('hanu', 'Han Hanuman'),
		('BigSuperStar', 'Titi Orangutan'),
		('darwin', 'Charles Darwin'),
		('wpooh', 'Winnie the Pooh'),
		('bgorilla', 'Busta Gorilla'),
		('ladidas', 'Larry Adidas'),
		('MojoJojo', 'Jojo Lemur'),
		('ghost84', 'Ghostly Ape'),
		('mmanda', 'Mary Mandarin'),
		('kkong', 'King Kong'),
		('mchipm', 'Madonna Chimpanzee'),
		('mhanuman', 'Mark Hanuman'),
		('ftamarin', 'Fredick Tamarin'),
		('llemur', 'Leopold von Lemur'),
		('abraham', 'Abraham Macaque'),
		('mindri', 'Marilyn Indri'),
		('ape99', 'Abe Ape'),
		('ManMan', 'Manila Mandarin'),
		('cheetah', 'Cheetah Monkey'), 
		('tarzan', u'John Weissmüller'), 
		('mark', 'Mark Mark')]
	try:
		get_db().executemany('INSERT INTO monkeys (username, name) VALUES (?, ?)', values)
	except IntegrityError as e:
		return False
	else:
		# Now actually "save the changes"
		get_db().commit()
                return insert_example_friendship_data()

def insert_example_friendship_data():
    result = query_db('SELECT COUNT(id) as entries FROM monkeys', one=True)
    if (len(result) != 1):
        return False
    nummonkeys = int(result['entries'])
    values = []
    for i in xrange(nummonkeys):
        numfriends = randint(2,nummonkeys-1)
        friendslist = sample(xrange(nummonkeys), numfriends)
        if (i in friendslist): # Remove the monkey itself, if present
            friendslist.pop(friendslist.index(i))
        values.extend(zip([i for x in friendslist], friendslist))
    #print(values)  
    try:
        get_db().executemany('INSERT INTO friendships (id1, id2) VALUES (?, ?)', values)
    except IntegrityError as e:
        return False
    else:
        get_db().commit()
        return True
    return True

# Wipe the database
@app.route('/wipe_database/')
def wipe_database():
	confirm = int(request.args.get('confirm', 0))
	if (confirm == 1): # Wipeout confirmed
		init_db() # Perhaps implement another method for a "soft" wipeout
		return render_template('wipe_database.html', confirm=True)
	else:
		return render_template('wipe_database.html', confirm=False)

# Error handling
@app.errorhandler(404)
def filenotfound(e):
    return render_template('filenotfound.html'), 404

# Run the application from command line
if __name__ == '__main__':
	init_db()	
	app.run()

