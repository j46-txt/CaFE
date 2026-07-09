# CaFE ☕︎

**CaFE** (**C**onsistency **a**nd **F**ocus **E**ngine) is a minimalist productivity tracker and timer built for long-term consistency. Using the built-in timer automatically records your activity, providing the data needed to identify patterns, analyze trends, and reinforce motivation over time.

## Features

* Pomodoro or stopwatch timer modes
* Weighted daily activity suggestion engine
* Statistics dashboard
* Weekly goal and progress tracking
* CSV data export

## Technology

* Python
* NiceGUI
* SQLite
* Psycopg2
* Tailwind CSS

## How to Run and Test

You can run and test this application locally on your own computer by following these steps:

### Prerequisites
Before starting, make sure you have **Python** installed on your system. If you do not have it, you can download and install it from the official website (python.org).

### Step 1: Download and Prepare the Project Files
* Download this repository as a ZIP file and extract all its contents into a folder on your computer, or clone it using Git:
```bash
git clone https://github.com/j46-txt/CaFE.git
```
* Open your terminal (Mac/Linux) or Command Prompt (Windows).
* Navigate to the folder where you downloaded this project's files (for example: `cd CaFE`).

### Step 2: Install the Required Packages
Copy and paste the following command into your terminal window and press Enter to automatically download the visual interface components:
```bash
pip install -r requirements.txt
```

### Step 3: Lauch the Application
Start the application tracking server by running this command:
```bash
python main.py
```

### Step 4: Open in Your Web Browser
Once the server is running, open any web browser (Chrome, Edge, Safari, or Firefox) and visit the following local address:
```bash
http://localhost:8080
```
The interface will load instantly, running entirely on your local machine using an automatic internal database.
