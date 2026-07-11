# CaFE ☕︎

**CaFE** (**C**onsistency **a**nd **F**ocus **E**ngine) is a minimalist productivity tracker and timer built for long-term consistency. Using the built-in timer automatically records your activity, providing the data needed to identify patterns, analyze trends, and reinforce motivation over time.

To enhance focus, it provides a frictionless experience by algorithmically rotating user-defined daily targets, eliminating the need to plan or choose. This makes it ideal for repeatedly studying or working on a predefined set of subjects.

It logs the date, weekday, focus duration, and activity using precise telemetry to help monitor your habits.

Long-term consistency is supported by tracking a weekly goal, calculating a rolling pace metric (hours/week), and displaying your total focus time and days invested.

Behind the scenes, the system uses automated, non-blocking backend mechanics, monotonic system clocks for precise tracking, an in-memory configuration cache to avoid disk read contention, and a serialized background queue worker to transparently mirror data to the cloud.

## Features

* Custom pomodoro timer with skippable breaks
* Stopwatch timer mode
* Suggestion management with custom probability weights
* Statistics dashboard
* Visual progress bar for weekly goal
* CSV data export
* Optional PostgreSQL cloud sync (see '.env.example')

## Technology

* Python 3.8+
* NiceGUI
* SQLite
* Psycopg2
* Tailwind CSS

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
