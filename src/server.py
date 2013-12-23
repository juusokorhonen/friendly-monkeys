from sqlite3 import dbapi2 as sqlite3
from flask import Flask, render_template, url_for, g, request, session, redirect, abort, flash
from contextlib import closing

# Create application
app = Flask(__name__)

# Application configuration
app.config.update(dict(
    DATABASE = '/tmp/monkeys.db',
    DEBUG = True,
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
    return render_template('list_monkeys.html')

@app.route('/add')
def add():
    return render_template('add_monkey.html')

@app.route('/add/multiple')
def add_several():
    return render_template('add_several_monkeys.html')
# Run the application from command line
if __name__ == '__main__':
    init_db()	
    app.run()

