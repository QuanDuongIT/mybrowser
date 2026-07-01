import os

if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, render_template_string, redirect
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from cryptography.fernet import Fernet, InvalidToken
import requests

from config import FERNET_KEY


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

<title>Safe DOM Editor</title>


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






@app.route("/", methods=["GET","POST"])
@app.route("/<token>", methods=["GET"])
def index(token=None):



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




    try:


        html=render_page(url)


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

        content=html

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