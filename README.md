# CaFE ☕︎

**CaFE** (**C**onsistency **a**nd **F**ocus **E**ngine) is a simple minimalist productivity tracker and timer designed for long-term consistency.

Using the built-in timer automatically records your activity, logging the date, weekday, and focus duration to help monitor your habits.

Once configured, it algorithmically rotates user-defined suggestions (which are also logged) in either **Daily Automatic Mode** (rotating once a day on launch) or **Manual Session-Based Mode** (retaining the current suggestion until manually advanced). This eliminates decision fatigue and makes it ideal for repeatedly studying or working on a predefined set of subjects.

Motivation and consistency are supported by tracking a weekly goal alongside a dashboard displaying a rolling "pace" metric (hours/week), total focused time, and days invested.

## Features

* Custom pomodoro timer with skippable breaks
* Stopwatch timer mode
* Suggestion management with custom probability weights
* Two suggestion-rotation modes (daily automatic and manual session-based)
* Visual progress bar for weekly goal
* CSV data export
* Optional PostgreSQL cloud sync (see `.env.example`)

## Technology

* Python 3.8+
* NiceGUI
* SQLite
* PostgreSQL (via Psycopg2)
* Tailwind CSS

## About

This project is one of the tools I built for myself. Not meant to change the world, just something that might also be useful to someone else.

Feel free to fork it or submit a pull request!

---

## How to Run and Test

You can run and test this application locally on your own computer by following these steps:

### Prerequisites
* **Python 3.8 or higher** installed.

### Step 1: Download and Prepare the Project Files
* Download this repository as a ZIP file and extract all its contents into a folder on your computer, or clone it using Git:
```bash
git clone https://github.com/j46-txt/CaFE.git
```
* Open your terminal (Mac/Linux) or Command Prompt (Windows) and navigate to the folder with this project's files.

### Step 2: Install the Required Packages:
```bash
pip install -r requirements.txt
```

### Step 3: Lauch the Application:
```bash
python main.py
```

### Step 4: Open in Your Web Browser:
```bash
http://localhost:8080
```
