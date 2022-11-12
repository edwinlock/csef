# How to add / update translations
This is transcribed from the [Flask-Babel documentation](https://flask-babel.tkte.ch/index.html?highlight=jinja#translating-applications).

# Remember that the translation files are in the IPICYT/webapp subfolder
# In the command line 
1. Extract all text strings to be translated
`pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .`

2. Create/update translation file for Spanish.

If you're doing this for the first time:
`pybabel init -i messages.pot -d translations -l es`

If you want to update the file:
`pybabel update -i messages.pot -d translations`

3. Translate all text strings in file `translations/es/LC_MESSAGES/messages.po`.

4. Compile translations for use in the web app

`pybabel compile -d translations`
 # to override fuzzy comments
`pybabel compile -f -d translations`