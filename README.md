# PESUGrab

A lightweight desktop app that downloads course slides and materials from [PESU Academy](https://www.pesuacademy.com/Academy/) using headless browser automation.

## Features

- **One-click login** — authenticate with your SRN and password
- **Semester switching** — browse all available semesters
- **Course & unit navigation** — explore courses and their units in a clean UI
- **Flexible downloads** — download a single unit, all units in a course, or everything in a semester
- **Organized output** — files are saved into `Course / Unit /` folders automatically
- **Dark, minimal UI** — grayscale Tkinter interface with a dark title bar

## Requirements

- Python 3.12+
- Windows 10/11 (for the dark title bar; the app still works on other platforms)

## Setup

```bash
# Install dependencies
pip install playwright python-dotenv

# Install the Chromium browser for Playwright
python -m playwright install chromium
```

## Usage

```bash
python app.py
```

1. Enter your SRN and password, then click **Login**
2. Select a semester from the dropdown — courses will load automatically
3. Click a course to see its units
4. Use the download buttons:
   - **Download Selected Unit** — downloads files for the highlighted unit
   - **Download All Units (Course)** — downloads every unit in the selected course
   - **Download All Courses (Semester)** — downloads everything for the current semester

Files are saved to `~/Downloads/` by default (changeable via Browse).

## Project Structure

```
├── app.py           # Tkinter GUI + worker thread
├── scraper.py       # Headless Playwright automation (AcademySession)
├── requirements.txt # Python dependencies
└── README.md
```

## License

MIT