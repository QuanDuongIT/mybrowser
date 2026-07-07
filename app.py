import os

if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, render_template_string, redirect
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from cryptography.fernet import Fernet, InvalidToken
import requests
import hashlib
from config import FERNET_KEY

import secrets

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



HTML = """

<!doctype html>

<html>

<head>

<meta charset="utf-8">

<title>{{ page_title }}</title>


<style>

body{
    margin:0;
    font-family:Arial;
    background:#f5f5f5;
}


.toolbar{

    padding:15px;
    background:white;
    border-bottom:1px solid #ddd;
    position:sticky;
    top:0;

}


input{

    width:600px;
    max-width:80vw;
    padding:8px;

}


.box{

    background:white;
    margin:20px auto;
    max-width:1400px;
    padding:40px;

}


.highlight{

    outline:2px solid red;

}


img{

    max-width:100%;

}

</style>



<script>

let editMode=false;
let selected=null;


function toggleEdit(x){

    editMode=x.checked;

}



function protectedNode(el){

    return el.closest(".protected");

}



document.addEventListener(
"mouseover",
e=>{


    if(!editMode)
        return;


    if(selected)
        selected.classList.remove("highlight");


    selected=e.target;


    if(protectedNode(selected)){
        selected=null;
        return;
    }


    selected.classList.add("highlight");

});



document.addEventListener(
"mouseup",
()=>{


    if(!editMode || !selected)
        return;


    if(protectedNode(selected))
        return;


    selected.style.display="none";

    selected.classList.remove("highlight");

    selected=null;


});


</script>


</head>



<body>



<div class="toolbar protected">


<form method="post" action="/">


<input

name="url"

value="{{ current_url }}"

placeholder="https://example.com"

/>


<button>

Go

</button>


<label>

<input

type="checkbox"

onchange="toggleEdit(this)"

>

Edit mode

</label>


</form>


</div>





<div class="box">


{{content | safe}}


</div>



</body>


</html>

"""


AUTH_HTML = """
<!doctype html>
<html>
<head>

<style>

body{
    margin:0;
    height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    background:#f2f2f2;
    font-family:Arial;
}


.auth-box{
    width:350px;
    background:white;
    padding:30px;
    border-radius:12px;
    box-shadow:0 5px 20px rgba(0,0,0,.15);
}


.auth-box input{

    width:100%;
    padding:12px;
    margin:8px 0;

    border:1px solid #ccc;
    border-radius:6px;

    font-size:14px;

    box-sizing:border-box;

}


.auth-box input:focus{

    outline:none;
    border-color:#4285f4;

}


.auth-box button{

    width:100%;
    margin-top:15px;

    padding:12px;

    background:#4285f4;
    color:white;

    border:none;
    border-radius:6px;

    cursor:pointer;

}


.auth-box button:hover{

    background:#3367d6;

}

</style>

</head>


<body>


<div class="auth-box">


<form method="post">


<input name="token1" value="{{ tokens[0] }}">
<input name="token2" value="{{ tokens[1] }}">
<input name="token3" value="{{ tokens[2] }}">
<input name="token4" value="{{ tokens[3] }}">
<input name="token5" value="{{ tokens[4] }}">
<input name="token6" value="{{ tokens[5] }}">


<button type="submit">
Submit
</button>


</form>


</div>

<div class="message">
    {{ message }}
</div>
</body>
</html>
"""

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





def proxy_dom(html, base_url):


    soup=BeautifulSoup(
        html,
        "html.parser"
    )



    # bỏ javascript

    for tag in soup(
        [
            "script",
            "style",
            "noscript"
        ]
    ):

        tag.decompose()




    # link -> token

    for a in soup.find_all(
        "a",
        href=True
    ):

        try:

            full=urljoin(
                base_url,
                a["href"]
            )


            token=encrypt_url(full)


            a["href"]="/"+token


        except:

            pass





    # ảnh

    for img in soup.find_all(
        "img",
        src=True
    ):


        try:

            img["src"]=urljoin(
                base_url,
                img["src"]
            )

        except:

            pass




    # css

    for link in soup.find_all(
        "link",
        href=True
    ):


        try:

            link["href"]=urljoin(
                base_url,
                link["href"]
            )

        except:

            pass



    return str(soup)

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

            return render_template_string(
                AUTH_HTML,
                tokens=TOKENS,
                message="Authenticate OK"
            )


        AUTH_OK = False

        return render_template_string(
            AUTH_HTML,
            tokens=TOKENS,
            message="Authenticate FAIL"
        )


    return render_template_string(
        AUTH_HTML,
        tokens=TOKENS,
        message=""
    )


@app.route("/", methods=["GET","POST"])
@app.route("/<token>", methods=["GET"])
def index(token=None):

    global AUTH_OK




    # nếu chưa authenticate thì bỏ token
    if not AUTH_OK:
        token = None
    # user nhập url

    if request.method=="POST":


        raw=request.form.get(
            "url"
        )


        if not raw:

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
    try:


        html=render_page(url)
        soup = BeautifulSoup(html, "html.parser")

        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()


        html=proxy_dom(
            html,
            url
        )



    except Exception as e:


        html=f"""

        <h2>Error</h2>

        <pre>{e}</pre>

        """



    return render_template_string(

        HTML,

        content=html,

        page_title=page_title,
        
        current_url=url

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