# RYM-tracklister

This is a script written in Python 3.6 designed to generate tracklistings for submission to the RateYourMusic database. It currently takes unstructured text (copied and pasted from another source) as input and creates a formatted tracklist conforming to RYM standards. It supports Unicode UTF-8 and optionally converts titles to title-case.

## Dev Setup
Python version: 3.6
Note: venv is recommended

0. `venv venv && source venv/bin/activate` (optional)
1. `pip install -r requirements.txt`
2. `export FLASK_APP=rym-tracklister`
3. `export FLASK_ENV=development`
4. `flask run`

## Example
Input:
```
1.	Overlord	03:46	  Show lyrics
2.	Bleeding Shrines Of Stone	03:00	  Show lyrics
3.	Maleficent Dreamvoid	04:37	  Show lyrics
4.	Liers In Wait	04:06	  Show lyrics
5.	Gateways	01:34	  instrumental
```
Output:
```
1|Overlord|3:46
2|Bleeding Shrines of Stone|3:00
3|Maleficent Dreamvoid|4:37
4|Liers in Wait|4:06
5|Gateways|1:34
```
