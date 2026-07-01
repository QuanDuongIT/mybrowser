# web_qweb_engine_view

python -m venv venv
venv\Scripts\activate

python -m pip install flask requests
python -m pip install beautifulsoup4
python -m pip install flask playwright
python -m playwright install
python -m pip install google-auth
python -m pip install cryptography
pip freeze > requirements.txt
python -m pip install -r requirements.txt

python app.py