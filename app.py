import os

if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, render_template, redirect, make_response
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from cryptography.fernet import Fernet, InvalidToken
import requests
import hashlib
from config import FERNET_KEY

import secrets
SCRIPT_STORE = {}
ACTIVE_SCRIPTS = set()

TOKENS = [secrets.token_urlsafe(16) for _ in range(6)]
def hash_tokens(tokens):

    # lấy 5 ký tự đầu của mỗi token
    data = "|".join(
        token[:5] for token in tokens
    )

    return hashlib.sha256(
        data.encode()
    ).hexdigest()



# tạo bản xác thực riêng
AUTH_TOKENS = TOKENS.copy()

# thay vị trí thứ 3 thành admin
AUTH_TOKENS[2] = "admin"


# hash bộ xác thực
TOKENS_HASH = hash_tokens(AUTH_TOKENS)
AUTH_OK = False

app = Flask(__name__)


fernet = Fernet(FERNET_KEY)



def encrypt_url(url):
    return fernet.encrypt(
        url.encode()
    ).decode()



def decrypt_url(token):
    return fernet.decrypt(
        token.encode()
    ).decode()


def render_page(url):


    headers={

        "User-Agent":
        "Mozilla/5.0"

    }


    r=requests.get(

        url,

        headers=headers,

        timeout=20,

        allow_redirects=True

    )


    r.raise_for_status()


    if not r.encoding:

        r.encoding=r.apparent_encoding


    return r.text



def rewrite_css(css, base_url):

    import re


    def replace_url(match):

        raw = match.group(1).strip()


        # bỏ dấu quote
        raw = raw.strip("\"'")


        # không proxy các loại này
        if (
            raw.startswith("data:")
            or
            raw.startswith("http://")
            or
            raw.startswith("https://")
            or
            raw.startswith("//")
            or
            raw.startswith("#")
        ):

            return "url(" + raw + ")"


        full = urljoin(
            base_url,
            raw
        )


        token = encrypt_url(full)


        return 'url("/resource/' + token + '")'


    # bắt url(...) nhưng không ăn dấu ngoặc bên trong
    pattern = r"url\((?!data:)([^)]*)\)"


    css = re.sub(
        pattern,
        replace_url,
        css,
        flags=re.I
    )


    return css

def proxy_dom(html, base_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    scripts = []


    # =========================
    # JAVASCRIPT WHITELIST
    # =========================

    for script in soup.find_all("script"):

        content = str(script)


        sid = hashlib.sha256(
            content.encode()
        ).hexdigest()[:12]


        SCRIPT_STORE[sid] = content


        src = script.get("src")


        name = src if src else "inline script"


        scripts.append(
            {
                "id": sid,
                "name": name,
                "active": sid in ACTIVE_SCRIPTS,
                "effect": False
            }
        )


        if sid not in ACTIVE_SCRIPTS:

            script.attrs = {
                "type": "text/plain",
                "data-disabled": sid
            }



    # =========================
    # LINK HTML
    # =========================

    for a in soup.find_all(
        "a",
        href=True
    ):

        try:

            full = urljoin(
                base_url,
                a["href"]
            )


            a["href"] = (
                "/" + encrypt_url(full)
            )


        except Exception:
            pass



    # =========================
    # IMAGE
    # =========================

    for img in soup.find_all(
        "img",
        src=True
    ):

        try:

            full = urljoin(
                base_url,
                img["src"]
            )


            img["src"] = (
                "/resource/" +
                encrypt_url(full)
            )


        except Exception:
            pass



    # =========================
    # CSS LINK
    # =========================

    for link in soup.find_all(
        "link",
        href=True
    ):

        try:

            full = urljoin(
                base_url,
                link["href"]
            )


            link["href"] = (
                "/resource/" +
                encrypt_url(full)
            )


        except Exception:
            pass



    # =========================
    # INLINE STYLE
    # =========================

    for tag in soup.find_all(
        style=True
    ):

        try:

            tag["style"] = rewrite_css(
                tag["style"],
                base_url
            )

        except Exception:
            pass



    return str(soup), scripts

@app.route("/enable", methods=["POST"])
def enable_scripts():

    global ACTIVE_SCRIPTS


    selected = set(
        request.form.getlist("scripts")
    )


    ACTIVE_SCRIPTS = selected

    if request.referrer:
        return redirect(request.referrer)
    else:
        return redirect("/")
  
@app.route("/resource/<token>")
def resource(token):

    try:

        url = decrypt_url(token)
        if url.startswith("data:"):
            return "Blocked data URI", 400
        
        print("RESOURCE URL:", url)


        r = requests.get(
            url,
            headers={
                "User-Agent":"Mozilla/5.0"
            },
            timeout=20
        )


        print(
            "STATUS:",
            r.status_code,
            "TYPE:",
            r.headers.get("Content-Type")
        )


        content_type = r.headers.get(
            "Content-Type",
            ""
        )


        if "text/css" in content_type or url.endswith(".css"):

            r.encoding = r.apparent_encoding

            css = rewrite_css(
                r.text,
                url
            )

            response = make_response(css)

            response.headers["Content-Type"]="text/css"

            return response


        response = make_response(r.content)

        if content_type:
            response.headers["Content-Type"]=content_type

        return response


    except Exception as e:

        print(
            "RESOURCE ERROR:",
            repr(e)
        )

        return "RESOURCE ERROR: "+str(e),500

@app.route("/auth", methods=["GET", "POST"])
def auth():

    global AUTH_OK

    if request.method == "POST":

        submitted = [
            request.form.get("token1"),
            request.form.get("token2"),
            request.form.get("token3"),
            request.form.get("token4"),
            request.form.get("token5"),
            request.form.get("token6"),
        ]


        if None in submitted:
            return "Missing token"


        check_tokens = submitted.copy()


        if hash_tokens(check_tokens) == TOKENS_HASH:

            AUTH_OK = True

            return render_template(
                "auth.html",
                tokens=TOKENS,
                message="Authenticate OK"
            )


        AUTH_OK = False

        return render_template(
            "auth.html",
            tokens=TOKENS,
            message="Authenticate FAIL"
        )

    return render_template(
        "auth.html",
        tokens=TOKENS,
        message="Authenticate FAIL"
    )

@app.route("/logout", methods=["POST"])
def logout():

    global AUTH_OK

    AUTH_OK = False

    ACTIVE_SCRIPTS.clear()

    return {
        "status": "success",
        "message": "Logout successful"
    }

@app.route("/", methods=["GET","POST"])
@app.route("/<token>", methods=["GET", "POST"])
def index(token=None):

    global AUTH_OK
    message = request.args.get("message", "")

    # nếu chưa authenticate thì bỏ token
    if not AUTH_OK:
        token = None
    # user nhập url

    if request.method=="POST":

        raw=request.form.get(
            "current_url"
        )

        if not raw:
            print("not raw")

            return redirect("/")


        token=encrypt_url(raw)


        return redirect("/"+token)


    # không có token

    if not token:

        url="https://example.com"

        token=encrypt_url(url)

    else:


        try:

            url=decrypt_url(token)


        except InvalidToken:

            return "Invalid token"

    page_title = url
    scripts = []

    try:

        html=render_page(url)
        soup = BeautifulSoup(html, "html.parser")

        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()


        html, scripts =proxy_dom(
            html,
            url
        )

    except Exception as e:

        html=f"""

        <h2>Error</h2>

        <pre>{e}</pre>

        """

    return render_template(
        "index.html",
        content=html,
        page_title=page_title,
        current_url=url,
        scripts=scripts,
        message=message
    )


if __name__=="__main__":


    port=int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )