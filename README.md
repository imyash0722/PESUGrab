<div align="center">

# PESUGrab

**Desktop app for downloading course materials from PESU Academy.**

<p>

  <a href="https://github.com/imyash0722/PESUGrab/releases/latest">
    <img alt="Latest Release" src="https://img.shields.io/github/v/release/imyash0722/PESUGrab?style=for-the-badge&logo=windows&logoColor=white&label=Latest&color=b39ddb&v=1">
  </a>
  &nbsp;
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-333?style=for-the-badge&logo=python&logoColor=white">
  &nbsp;
  <img alt="Platform" src="https://img.shields.io/badge/Windows-10%2F11-333?style=for-the-badge&logo=windows&logoColor=white">
  &nbsp;
  <img alt="License" src="https://img.shields.io/github/license/imyash0722/PESUGrab?style=for-the-badge&color=444&v=1">
</p>

<br>

</div>

---

## Features

|                                |                                                                      |
| ------------------------------ | -------------------------------------------------------------------- |
| 🔐 **One-Click Login**          | Authenticate with your SRN and password                              |
| 📚 **Semester Browser**         | Switch between all available semesters                               |
| 📂 **Course & Unit Navigation** | Browse courses and their units in a clean tree view                  |
| ⬇️ **Flexible Downloads**       | Download a single unit, all units in a course, or an entire semester |
| 📁 **Organized Output**         | Files saved into `Course / Unit /` folders automatically             |
| ⏳ **Live Progress**            | Animated loading indicators and a real-time log                      |
| 🎨 **Dark Violet Theme**        | Minimal grayscale UI with dark window chrome                         |

---

## Quick Start

### Option 1 — Setup Installer (recommended)

1. Go to [**Releases**](https://github.com/imyash0722/PESUGrab/releases/latest)
2. Download `PESUGrab-Setup-v1.0.0.exe`
3. Double-click to install. This will add shortcuts to your Start Menu and Desktop.

> [!NOTE]
> The installer bundles Python + dependencies. Playwright's Chromium browser is **not** bundled — it will be downloaded on first run. Make sure you have internet access.

### Option 2 — Run from source

```bash
# Clone the repo
git clone https://github.com/imyash0722/PESUGrab.git
cd PESUGrab

# Install dependencies
pip install -r requirements.txt

# Install the Chromium browser for Playwright
python -m playwright install chromium

# Launch
python app.py
```

---

## Usage

1. **Login** — enter your SRN and password in the login dialog
2. **Select semester** — courses load automatically
3. **Click a course** — units will appear in the right panel
4. **Download** using one of three buttons:

| Button                              | What it does                                  |
| ----------------------------------- | --------------------------------------------- |
| **Download Selected Unit**          | Downloads files for the highlighted unit      |
| **Download All Units (Course)**     | Downloads every unit in the selected course   |
| **Download All Courses (Semester)** | Downloads everything for the current semester |

Files are saved to `~/Downloads/` by default — changeable via **Browse**.

---

## Project Structure

```
PESUGrab/
├── app.py             # Tkinter GUI + worker thread
├── scraper.py         # Headless Playwright automation (AcademySession)
├── requirements.txt   # Python dependencies
├── LICENSE
└── README.md
```

---

## Building from Source

To build the standalone `.exe` yourself:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name PESUGrab app.py
```

The output will be in `dist/PESUGrab.exe`.

---

## Tech Stack

- **Python 3.12+** — core runtime
- **Tkinter** — native desktop GUI
- **Playwright** — headless Chromium automation
- **PyInstaller** — standalone exe packaging

---

## License

[GPL-3.0](LICENSE)

---

<div align="center">
  <sub>Built with ☕ for PES University students</sub>
</div>