# RYM-tracklister

This is a script written in Python 2.7 designed to generate tracklistings for submission to the RateYourMusic database. It currently takes raw copied/pasted input as txt and creates a formatted tracklist conforming to RYM standards. It properly formats titles (including Unicode), allows for quick linking of classical works, and supports selective filtering of unwanted text. This will soon be revised and implemented as a web app for easier contributor accessibility.

## Dev Setup
Python version: 2.7
Note: virtualenv is recommended

1. `pip install -r requirements.txt`
2. `python server.py`
