
dependencies = [
email-validator
flask-login
flask
flask-sqlalchemy
gunicorn
psycopg2-binary
requests
flask-wtf
oauthlib
pytube
werkzeug
wtforms
]


run = ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]

