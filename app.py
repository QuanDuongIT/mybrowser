from flask import Flask, request, render_template_string
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import os

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
    <title>Safe DOM Editor</title>

    <style>
        body { font-family: Arial; margin: 10px; }

        .toolbar {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }

        .box {
            border: 1px solid #ddd;
            padding: 10px;
            background: #f9f9f9;
        }

        .highlight {
            outline: 2px solid red !important;
            background: rgba(255,0,0,0.05);
        }
    </style>

    <script>
        let editMode = false;
        let selected = null;

        function toggleEdit(cb) {
            editMode = cb.checked;
        }

        function isProtected(el) {
            return el.closest(".protected") !== null;
        }

        document.addEventListener("mouseover", (e) => {
            if (!editMode) return;

            if (selected) {
                selected.classList.remove("highlight");
            }

            selected = e.target;

            if (isProtected(selected)) return;

            selected.classList.add("highlight");
        });

        document.addEventListener("mouseup", () => {
            if (!editMode || !selected) return;

            if (isProtected(selected)) return;

            selected.style.display = "none";
            selected.classList.remove("highlight");
            selected = null;
        });
    </script>
</head>

<body>

<div class="toolbar protected">
    <form method="get">
        <input
            name="url"
            style="width:500px"
            value="{{ url }}"
        >

        <button>Go</button>

        <label style="margin-left:10px;">
            <input
                type="checkbox"
                onchange="toggleEdit(this)"
            >
            Edit mode
        </label>
    </form>
</div>

<hr>

<div class="box">
{{ content | safe }}
</div>

</body>
</html>
"""


def render_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()

    if not response.encoding:
        response.encoding = response.apparent_encoding

    return response.text


def proxy_dom(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    # Xóa JS/CSS
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Rewrite links để duyệt tiếp qua proxy
    for a in soup.find_all("a", href=True):
        try:
            full_url = urljoin(base_url, a["href"])
            a["href"] = "/?url=" + full_url
        except Exception:
            pass

    # Fix ảnh
    for img in soup.find_all("img", src=True):
        try:
            img["src"] = urljoin(base_url, img["src"])
        except Exception:
            pass

    # Fix CSS files
    for link in soup.find_all("link", href=True):
        try:
            link["href"] = urljoin(base_url, link["href"])
        except Exception:
            pass

    return str(soup)


@app.route("/", methods=["GET"])
def index():
    url = request.args.get(
        "url",
        "https://example.com"
    )

    try:
        html = render_page(url)
        html = proxy_dom(html, url)

    except Exception as e:
        html = f"""
        <h3>Error</h3>
        <pre>{str(e)}</pre>
        """

    return render_template_string(
        HTML,
        content=html,
        url=url
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )