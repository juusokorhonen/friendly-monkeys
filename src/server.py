from sqlite3 import dbapi2 as sqlite3
from sqlite3 import IntegrityError
from flask import Flask, render_template, url_for, g, request, session, redirect, abort, flash, escape, make_response
from contextlib import closing
from flask_wtf import Form
from wtforms import TextField, validators

# Define WTForms classes
class AddMonkeyForm(Form):
    """Form that adds a single monkey to the database."""
    username = TextField('Username', [validators.Length(min=4, max=25, message='Username should be 4...25 characters long')])
    name = TextField('Full name', [validators.InputRequired(message='Full name cannot be empty')])

# Define custon exceptions
class UsernameNotUniqueException(Exception):
    pass

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
    try:
        cur = get_db().execute(query, args)
        rv = cur.fetchall()
        cur.close()
    except IntegrityError as e:
        raise UsernameNotUniqueException()
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
    result = query_db('SELECT monkeyid,username,name FROM monkeys')
    if (result is None):
        # No monkeys were returned
        return render_template('list_monkeys.html')
    else:
        # There are monkeys
        return render_template('list_monkeys.html', monkeys=result)

@app.route('/show/<username>')
def show(username):
    """Show the monkey profile, which is identified by username."""
    result = query_db('SELECT monkeyid,username,name FROM monkeys WHERE username=?', args=[username], one=True)
    #print(result)
    if (result is None):
        # Monkey search failed, so give 404
        abort(404)
        #return make_response(render_template('filenotfound.html'), 404)
    return render_template('show_monkey.html', monkey=result)

@app.route('/add', methods=['GET', 'POST'])
def add():
    form = AddMonkeyForm(request.form)
    if (request.method == 'GET'):
        # Display the input form
        return render_template('show_add_monkey_form.html', form=form)
    elif (request.method == 'POST' and form.validate()):
        # Form has been sent and validated
        username = form.username.data
        name = form.name.data
        msg = "" # Message for next page flash
        # !!! Using prepared statements here, yet the safety should be checked
        try:
            query_db('INSERT INTO monkeys (username, name) VALUES (?, ?)', (username, name), one=True)
        except UsernameNotUniqueException:
            msg += 'Adding monkey failed. Username "{username}" already in use.'.format(username=escape(username))
            flash(msg, 'error')
        else:
            get_db().commit() # Commit changes
            # Make a note on the next page
            msg = 'Successfully added a monkey named "{name}", with username "{username}".<br />\n<a href="{entryurl}" class="alert-link">See entry</a>.'.format(name=escape(name), username=escape(username), entryurl=url_for('show', username=username))
            #print(msg)
            flash(msg)
        return render_template('show_add_monkey_form.html', form=form) 
    else: # request method is post, yet the form did not validate
        errormsg = 'Adding monkey failed.'
        # Append error messages to flash
        if (form.errors):
            for field_name, field_errors in form.errors.items():
                for error in field_errors:
                    errormsg += '<br />{error}.\n'.format(error=error)
        flash(errormsg, 'error')
        return render_template('show_add_monkey_form.html', form=form)

# Make example data into the database
@app.route('/load_example_data/', defaults={'confirm': 0})
@app.route('/load_example_data/confirm/<int:confirm>')
def load_example_data(confirm):
    if (confirm == 1):
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
                    ('kkong', 'King Kong')]
        try:
            get_db().executemany('INSERT INTO monkeys (username, name) VALUES (?, ?)', values)
        except IntegrityError as e:
            return render_template('load_example_data.html', confirm=True, success=False)
        else:
            get_db().commit() # Make the changes
            return render_template('load_example_data.html', confirm=True, success=True)
    else:
        return render_template('load_example_data.html', confirm=False)

# Wipe the database
@app.route('/wipe_database/', defaults={'confirm': 0})
@app.route('/wipe_database/confirm/<int:confirm>')
def wipe_database(confirm):
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

