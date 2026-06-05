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
    <meta charset="utf-8">
    <title>Safe DOM Editor</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            margin: 0;
            background: #f5f5f5;
        }

        .toolbar {
            padding: 12px 20px;
            border-bottom: 1px solid #ddd;
            background: white;
            position: sticky;
            top: 0;
            z-index: 999;
        }

        .toolbar input[name="url"] {
            width: min(700px, 80vw);
            padding: 8px;
        }

        .page-container {
            padding: 20px 30px;
        }

        .box {
            max-width: 1400px;
            margin: 0 auto;
            border: 1px solid #ddd;
            background: white;
            overflow-x: auto;
            padding: 0 50px;
        }

        .highlight {
            outline: 2px solid red !important;
            background: rgba(255,0,0,0.05) !important;
        }

        img {
            max-width: 100%;
            height: auto;
        }

        table {
            max-width: 100%;
        }
    </style>

    <script>
        let editMode = false;
        let selected = null;

        function toggleEdit(cb) {
            editMode = cb.checked;

            if (!editMode && selected) {
                selected.classList.remove("highlight");
                selected = null;
            }
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

            if (isProtected(selected)) {
                selected = null;
                return;
            }

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
            value="{{ url }}"
            placeholder="https://example.com"
        >

        <button type="submit">Go</button>

        <label style="margin-left:15px;">
            <input
                type="checkbox"
                onchange="toggleEdit(this)"
            >
            Edit mode
        </label>
    </form>
</div>

<div class="page-container">
    <div class="box">
        {{ content | safe }}
    </div>
</div>

</body>
</html>
"""


def render_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
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

    # Xóa JS, CSS nội bộ và noscript
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Rewrite links
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

    # Fix CSS ngoài
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
        <h2>Error</h2>
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