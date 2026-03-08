"""
PESUGrab — Headless browser automation for PESU Academy.
Handles authentication, navigation, content discovery and file retrieval.
"""

import os
import re
from playwright.sync_api import sync_playwright, Page, Browser


class AcademySession:
    """
    Manages a headless browser session against pesuacademy.com.
    All public methods are synchronous and must be called from the
    same thread that called `open()`.
    """

    ORIGIN = "https://www.pesuacademy.com"

    def __init__(self):
        self._pw_ctx = None
        self._browser: Browser | None = None
        self._tab: Page | None = None
        self._authenticated = False

    # ── Session lifecycle ──────────────────────────────────

    def open(self):
        """Spin up a headless Chromium instance."""
        self._pw_ctx = sync_playwright().start()
        self._browser = self._pw_ctx.chromium.launch(headless=True)
        ctx = self._browser.new_context()
        self._tab = ctx.new_page()
        # Skip heavy assets for speed
        self._tab.route(
            "**/*",
            lambda r: r.abort()
            if r.request.resource_type in ("image", "media", "font")
            else r.continue_(),
        )

    def close(self):
        """Tear down browser and Playwright."""
        for obj in (self._browser, self._pw_ctx):
            try:
                if obj:
                    obj.close() if hasattr(obj, "close") else obj.stop()
            except Exception:
                pass
        self._browser = self._tab = self._pw_ctx = None
        self._authenticated = False

    @property
    def tab(self) -> Page:
        if not self._tab:
            raise RuntimeError("Session not open — call open() first")
        return self._tab

    # ── Authentication ─────────────────────────────────────

    def authenticate(self, srn: str, pwd: str):
        """Sign in with SRN/PRN + password."""
        t = self.tab
        t.goto(f"{self.ORIGIN}/Academy/")
        t.fill("#j_scriptusername", srn)
        t.fill("input[name='j_password']", pwd)
        t.click("button.btn-primary")
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(1200)

        sidebar = t.locator("span.menu-name")
        if sidebar.count() == 0:
            raise RuntimeError("Authentication failed — verify credentials")
        self._authenticated = True

    # ── Semester handling ──────────────────────────────────

    def navigate_to_courses(self):
        """Click the courses link in the sidebar and wait for the page."""
        t = self.tab
        t.locator("span.menu-name", has_text="My Courses").click()
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(1000)
        try:
            t.wait_for_selector("#semesters", timeout=8000)
        except Exception:
            pass

    def list_semesters(self) -> list[str]:
        """Return available semester labels after navigating to courses."""
        self.navigate_to_courses()
        opts = self.tab.locator("#semesters option")
        return [
            opts.nth(i).inner_text().strip()
            for i in range(opts.count())
            if opts.nth(i).inner_text().strip()
        ]

    def switch_semester(self, label: str):
        """Pick a semester from the dropdown by its visible text."""
        t = self.tab
        if t.locator("#semesters").count() == 0:
            self.navigate_to_courses()

        t.wait_for_selector("#semesters", timeout=8000)
        opts = t.locator("#semesters option")
        val = None
        for i in range(opts.count()):
            if opts.nth(i).inner_text().strip() == label:
                val = opts.nth(i).get_attribute("value")
                break
        if val is None:
            raise ValueError(f"Semester '{label}' not available")

        t.select_option("#semesters", val)
        t.wait_for_timeout(2000)
        t.wait_for_load_state("networkidle")

    # ── Course listing ─────────────────────────────────────

    def list_courses(self) -> list[dict]:
        """
        Scrape the courses table for the active semester.
        Returns list of dicts with keys: code, title, kind, status.
        """
        t = self.tab
        t.wait_for_timeout(600)

        empty = t.locator("h2", has_text="No subjects found")
        try:
            if empty.count() > 0 and empty.is_visible():
                return []
        except Exception:
            pass

        t.wait_for_selector("table.table-hover", timeout=8000)
        rows = t.locator("table.table-hover tbody tr")
        results = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            if cells.count() >= 4:
                results.append({
                    "code": cells.nth(0).inner_text().strip(),
                    "title": cells.nth(1).inner_text().strip(),
                    "kind": cells.nth(2).inner_text().strip(),
                    "status": cells.nth(3).inner_text().strip(),
                })
        return results

    def open_course(self, idx: int):
        """Click the idx-th course row."""
        rows = self.tab.locator("table.table-hover tbody tr")
        rows.nth(idx).click()
        self.tab.wait_for_load_state("networkidle")
        self.tab.wait_for_timeout(1200)

    # ── Unit listing ───────────────────────────────────────

    def list_units(self) -> list[str]:
        """Return unit tab labels for the currently open course."""
        t = self.tab
        t.wait_for_selector("#courselistunit li", timeout=8000)
        tabs = t.locator("#courselistunit li a")
        return [tabs.nth(i).inner_text().strip() for i in range(tabs.count())]

    def open_unit(self, idx: int):
        """Click a unit tab by index."""
        tabs = self.tab.locator("#courselistunit li a")
        tabs.nth(idx).click()
        self.tab.wait_for_load_state("networkidle")
        self.tab.wait_for_timeout(800)

    # ── File discovery ─────────────────────────────────────

    def discover_files(self, unit_idx: int, progress_cb=None) -> list[dict]:
        """
        Open a unit and walk through all class pages collecting download URLs.
        Returns list of dicts: { name, href, filetype }.
        progress_cb(message) is called with status text if provided.
        """
        t = self.tab
        self.open_unit(unit_idx)

        collected = []
        known_hrefs = set()

        # Enter the first content page
        if not self._enter_content_area(t):
            return collected

        page_no = 0
        while True:
            page_no += 1
            if progress_cb:
                progress_cb(f"Page {page_no}...")

            # Activate slides tab if present
            slides_tab = t.locator("#contentType_2")
            if slides_tab.count() > 0:
                slides_tab.click()
                t.wait_for_timeout(500)

            # Skip empty pages
            no_content = t.locator("h2", has_text="No Slides Content")
            if no_content.count() > 0 and no_content.is_visible():
                pass
            else:
                self._extract_links(t, collected, known_hrefs)

            # Advance or stop
            if not self._advance_page(t):
                break

        return collected

    def _enter_content_area(self, t: Page) -> bool:
        """Click into the first piece of slide content. Returns True on success."""
        # Method 1: presentation icon
        try:
            t.wait_for_selector(
                "span.pesu-icon-presentation-graphs", timeout=4000
            )
            t.locator(
                "a:has(span.pesu-icon-presentation-graphs)"
            ).first.click()
            t.wait_for_load_state("networkidle")
            t.wait_for_timeout(700)
            return True
        except Exception:
            pass

        # Method 2: "Click here to view content" links
        try:
            view_links = t.locator("td a[title='Click here to view content']")
            if view_links.count() > 0:
                view_links.first.click()
                t.wait_for_load_state("networkidle")
                t.wait_for_timeout(700)
                return True
        except Exception:
            pass

        return False

    def _extract_links(self, t: Page, out: list, seen: set):
        """Pull download URLs from the current content page."""
        try:
            t.wait_for_selector(".link-preview", timeout=4000)
        except Exception:
            return

        cards = t.locator(".link-preview")
        for i in range(cards.count()):
            card = cards.nth(i)
            hrefs = []
            ftype = "pdf"

            # Inline viewer links
            anchor = card.locator("a")
            if anchor.count() > 0:
                handler = anchor.get_attribute("onclick") or ""
                for match in re.findall(r"loadIframe\('([^']+)", handler):
                    hrefs.append(match)

            # Direct download links
            if not hrefs:
                handler = card.get_attribute("onclick") or ""
                for doc_id in re.findall(
                    r"downloadcoursedoc\('([^']+)'", handler
                ):
                    hrefs.append(
                        "/Academy/a/referenceMeterials/"
                        f"downloadslidecoursedoc/{doc_id}"
                    )
                    ftype = "pptx"

            label = card.inner_text().strip()[:80] or f"file_{i+1}"

            for href in hrefs:
                full = (self.ORIGIN + href) if href.startswith("/") else href
                full = full.split("#")[0]
                if full not in seen:
                    seen.add(full)
                    out.append({
                        "name": label,
                        "href": full,
                        "filetype": ftype,
                    })

    def _advance_page(self, t: Page) -> bool:
        """Click the next-page arrow. Returns False when we're done."""
        try:
            arrow = t.locator(".coursecontent-navigation-area a.pull-right")
            if arrow.count() == 0:
                return False
            text = arrow.inner_text().strip()
            if "Back to Units" in text:
                return False
            arrow.click()
            t.wait_for_load_state("networkidle")
            t.wait_for_timeout(700)
            return True
        except Exception:
            return False

    # ── File retrieval ─────────────────────────────────────

    def retrieve_file(self, href: str, dest: str) -> bool:
        """Fetch a file by URL and write it to dest. Returns True on success."""
        try:
            resp = self.tab.request.get(href)
            if resp.status != 200:
                return False
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(resp.body())
            return True
        except Exception:
            return False
