const puppeteer = require("puppeteer");

const url = process.argv[2];

(async () => {
    const browser = await puppeteer.launch({
        headless: "new",
        args: [
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
    });

    const page = await browser.newPage();

    await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 30000
    });

    const html = await page.content();

    console.log(html);

    await browser.close();
})();