from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_FILES = (
    "index.html",
    "styles.css",
    "script.js",
    "README.md",
    "NOTICE.md",
)

ALLOWED_FILES = set(REQUIRED_FILES) | {
    ".nojekyll",
    "changelog/2026-09-04-public-source-free-demo/NOTE.md",
    "changelog/2026-09-04-public-source-free-demo/desktop.png",
    "docs/proof/desktop.png",
    "docs/proof/mobile.png",
    "docs/proof/fail-first.txt",
    "docs/proof/privacy-sabotage.txt",
    "tools/site_gate.py",
}

FORBIDDEN_SUFFIXES = {
    ".cs",
    ".csproj",
    ".sln",
    ".exe",
    ".dll",
    ".pdb",
    ".kmc",
    ".mfp",
}

FORBIDDEN_DIRS = {"src", "tests", "artifacts", "bin", "obj", "samples"}


class GateFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def source_gate(root: Path) -> int:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    require(not missing, f"missing required files: {', '.join(missing)}")

    public_files: list[Path] = []
    forbidden: list[str] = []
    unexpected: list[str] = []
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        public_files.append(path)
        relative = path.relative_to(root)
        relative_name = relative.as_posix()
        lowered_parts = {part.lower() for part in relative.parts[:-1]}
        if lowered_parts & FORBIDDEN_DIRS or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            forbidden.append(relative_name)
        if relative_name not in ALLOWED_FILES:
            unexpected.append(relative_name)

    require(not forbidden, f"desktop implementation leaked: {', '.join(forbidden)}")
    require(not unexpected, f"unexpected public files: {', '.join(unexpected)}")
    require(len(public_files) == len(ALLOWED_FILES), "public file allowlist count mismatch")

    html = (root / "index.html").read_text(encoding="utf-8")
    require(html.count("<h1") == 1, "page must contain exactly one h1")
    require(html.count("data-demo-step") == 5, "walkthrough must expose exactly five usage steps")
    require("No desktop source" in html, "source-free repository boundary is not visible")
    require("previously released under MIT" in html, "prior public-release boundary is missing")
    require("No application source or binaries are included" in html, "repository boundary copy is missing")
    require("14/14" in html and "68" in html, "measured proof summary is incomplete")
    require("prefers-reduced-motion" in (root / "styles.css").read_text(encoding="utf-8"), "reduced-motion CSS is missing")
    return len(public_files)


def browser_gate(base_url: str, screenshot_dir: Path | None) -> tuple[int, int]:
    from playwright.sync_api import sync_playwright

    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    require(chrome.is_file(), f"installed Chrome not found at {chrome}")

    expected = urlparse(base_url)
    external_requests: set[str] = set()
    rendered_cases = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(chrome))
        try:
            for name, width, height in (("desktop", 1440, 1000), ("mid", 1280, 900), ("mobile", 390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def inspect_request(request) -> None:
                    parsed = urlparse(request.url)
                    if parsed.scheme in {"http", "https"} and parsed.netloc != expected.netloc:
                        external_requests.add(request.url)

                page.on("request", inspect_request)
                response = page.goto(base_url, wait_until="networkidle")
                require(response is not None and response.ok, f"{name}: page did not return HTTP success")
                require(page.title() == "MacroForge — source-free product walkthrough", f"{name}: title mismatch")
                require(page.locator("main").count() == 1, f"{name}: main landmark mismatch")
                require(page.locator("h1").count() == 1, f"{name}: h1 mismatch")
                require(page.locator("[data-demo-step]").count() == 5, f"{name}: walkthrough step mismatch")
                images = page.locator("img")
                for image_index in range(images.count()):
                    image = images.nth(image_index)
                    image.scroll_into_view_if_needed()
                    image.wait_for(state="visible")
                    page.wait_for_function(
                        "index => { const node = document.images[index]; return node && node.complete && node.naturalWidth > 0; }",
                        arg=image_index,
                    )
                    require(
                        image.evaluate("node => node.complete && node.naturalWidth > 0"),
                        f"{name}: image {image_index + 1} decode failed",
                    )
                overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                require(overflow <= 1, f"{name}: horizontal overflow={overflow}px")

                contrast_script = """
                    node => {
                        const parse = value => (value.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
                        const luminance = rgb => {
                            const channels = rgb.map(value => {
                                const channel = value / 255;
                                return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
                            });
                            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
                        };
                        const style = getComputedStyle(node);
                        const foreground = luminance(parse(style.color));
                        const background = luminance(parse(style.backgroundColor));
                        return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
                    }
                """
                for selector in (".trace-topbar b", ".engine-state", ".primary-action", ".editor-footer strong"):
                    ratio = page.locator(selector).first.evaluate(contrast_script)
                    require(ratio >= 4.5, f"{name}: contrast {selector}={ratio:.2f}:1")
                page.locator(".primary-action").hover()
                hover_ratio = page.locator(".primary-action").evaluate(contrast_script)
                require(hover_ratio >= 4.5, f"{name}: hover contrast={hover_ratio:.2f}:1")

                page.locator("#run-demo").click()
                page.locator("#demo-status").wait_for(state="visible")
                page.wait_for_function("document.querySelector('#demo-status')?.dataset.complete === 'true'")
                require(
                    page.locator("[data-demo-step][data-state='done']").count() == 5,
                    f"{name}: walkthrough did not finish all steps",
                )
                require("68-character" in page.locator("#demo-status").inner_text(), f"{name}: proof result missing")
                require(not console_errors, f"{name}: console errors: {console_errors}")
                require(not page_errors, f"{name}: page errors: {page_errors}")

                if screenshot_dir and name in {"desktop", "mobile"}:
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    page.evaluate(
                        "document.documentElement.style.scrollBehavior = 'auto'; "
                        "document.activeElement?.blur(); window.scrollTo(0, 0)"
                    )
                    page.wait_for_function("window.scrollY === 0")
                    page.wait_for_timeout(50)
                    page.screenshot(path=str(screenshot_dir / f"{name}.png"), full_page=True)
                context.close()
                rendered_cases += 1

            reduced = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            page = reduced.new_page()
            page.goto(base_url, wait_until="networkidle")
            page.locator("#run-demo").click()
            page.wait_for_function("document.querySelector('#demo-status')?.dataset.complete === 'true'")
            require(page.locator("[data-demo-step][data-state='done']").count() == 5, "reduced motion: walkthrough failed")
            reduced.close()
        finally:
            browser.close()

    require(not external_requests, f"external network requests detected: {sorted(external_requests)}")
    return rendered_cases, len(external_requests)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MacroForge's public, source-free demo site.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-url")
    parser.add_argument("--screenshot-dir", type=Path)
    args = parser.parse_args()

    try:
        root = args.root.resolve()
        file_count = source_gate(root)
        rendered_cases = 0
        external_count = 0
        if args.base_url:
            rendered_cases, external_count = browser_gate(args.base_url, args.screenshot_dir)
        print(
            "SITE_GATE_OK "
            f"publicFiles={file_count} desktopSourceFiles=0 renderedCases={rendered_cases} "
            f"externalRequests={external_count}"
        )
        return 0
    except GateFailure as failure:
        print(f"SITE_GATE_RED {failure}")
        return 1
    except Exception as error:
        print(f"SITE_GATE_RED unexpected {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
