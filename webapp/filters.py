from webapp import app
import flask_babel as bbl

@app.template_filter()
def format_datetime(value, format='short'):
    if value is None:
        return None
    return bbl.format_datetime(value, format)

@app.template_filter()
def format_date(value, format='short'):
    if value in [None, '']:
        return None
    return bbl.format_date(value, format)

@app.template_filter()
def format_timedelta(value, granularity='hours'):
    if value in [None, '']:
        return None
    return bbl.format_timedelta(value, granularity)