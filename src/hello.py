from flask import Flask, render_template, url_for

def create_app():
	app = Flask(__name__)
	return app

app = create_app()

@app.route('/')
def hello_world():
	return render_template('jumbotron-narrow.html')

if __name__ == '__main__':
	app.debug = True
	app.run()

