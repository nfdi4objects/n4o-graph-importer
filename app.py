from flask import Flask, render_template, redirect, request, make_response, url_for
from waitress import serve
import argparse as AP
import requests
import subprocess

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/assets')
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

@app.route('/')
def home():
   correct = subprocess.run(['echo','Josef Heers'],capture_output=True, text=True)   
   return  f'Hey ho {correct.stdout}\n'


if __name__ == '__main__':
   parser = AP.ArgumentParser()
   parser.add_argument('-w', '--wsgi', action=AP.BooleanOptionalAction, help="Use WSGI server")
   parser.add_argument('-p', '--port', type=int, default=5020, help="Server port")
   args = parser.parse_args()
   opts = {"port": args.port}

   if args.wsgi:
      serve(app, host="0.0.0.0", **opts)
   else:
      app.run(host="0.0.0.0", **opts)
