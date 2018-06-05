from flask import Flask


def create_app():
    # create and configure the app
    app = Flask(__name__)

    from . import server
    app.register_blueprint(server.bp)

    return app
