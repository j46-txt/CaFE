# CaFE ☕︎

**CaFE** (**C**onsistency **a**nd **F**ocus **E**ngine) is a minimalist productivity tracker and timer built for long-term consistency.

The built-in timer records your activity, logging the date, weekday, focus duration, and activity to help monitor your habits.

Once configured, it algorithmically rotates user-defined daily suggestions, eliminating the need to plan or choose, which is ideal for repeatedly studying or working on a predefined set of subjects.

Motivation and consistency are supported by tracking a weekly goal alongside a rolling "pace" metric (hours/week), and total time invested.

## Features

* Custom pomodoro timer with skippable breaks
* Stopwatch timer mode
* Suggestion management with custom probability weights
* Statistics dashboard
* Visual progress bar for weekly goal
* CSV data export
* Optional PostgreSQL cloud sync (see `.env.example`)

## Technology

* Python 3.8+
* NiceGUI
* SQLite
* Psycopg2
* Tailwind CSS

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
