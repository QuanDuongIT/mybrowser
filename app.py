from flask import Flask, request, render_template_string
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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

            if (selected) selected.classList.remove("highlight");

            selected = e.target;

            // KHÔNG highlight UI protected
            if (isProtected(selected)) return;

            selected.classList.add("highlight");
        });

        document.addEventListener("mousedown", (e) => {
            if (!editMode) return;

            if (isProtected(e.target)) return;
        });

        document.addEventListener("mouseup", () => {
            if (!editMode || !selected) return;

            // CHẶN xóa UI protected
            if (isProtected(selected)) return;

            selected.style.display = "none";
            selected.classList.remove("highlight");
            selected = null;
        });
    </script>
</head>

<body>

<!-- PROTECTED TOOLBAR -->
<div class="toolbar protected">
    <form method="get">
        <input name="url" style="width:500px" value="{{ url }}">
        <button>Go</button>

        <label style="margin-left:10px;">
            <input type="checkbox" onchange="toggleEdit(this)">
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
        return html


def proxy_dom(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    for a in soup.find_all("a", href=True):
        a["href"] = "/?url=" + urljoin(base_url, a["href"])

    return str(soup)


@app.route("/", methods=["GET"])
def index():
    url = request.args.get("url", "https://example.com")

    try:
        html = render_page(url)
        html = proxy_dom(html, url)
    except Exception as e:
        html = f"<h3>Error: {str(e)}</h3>"

    return render_template_string(HTML, content=html, url=url)


if __name__ == "__main__":
    app.run(debug=True)