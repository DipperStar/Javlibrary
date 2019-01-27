from flask import Flask
from mongo import MongoDB

app = Flask(__name__)

class API:
	def __init__(self):
		self.rankdb = MongoDB('Javdb', 'rankdb')

	@app.route('/<identity>', methods=['GET', 'POST'])
	def identity(identity = None):
	    return self.rankdb.find({'identity': identity})

if __name__ == '__main__':
	app.run(host='0.0.0.0', port = 8080, threaded=True)