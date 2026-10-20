# Blond Event Calculator

A minimalist full-stack event finance calculator for event organisers. It keeps event expenses and revenue in a local SQLite database, calculates profit or loss, and compares two events side by side.

## Features

- Create, edit, and delete events
- Track capacity, attendance, and venue fill rate
- Record expenses in eight consistent categories
- Create flexible ticket and other-income categories
- Calculate tickets sold, total revenue, total expenses, and profit or loss
- Compare two events using absolute and percentage differences
- Store data locally with SQLite

## Technology

- Python and Flask
- SQLite
- HTML and CSS
- JavaScript

## Run locally

1. Clone the repository and open its folder:

   ```bash
   git clone https://github.com/chayechka9/blond-event-calculator.git
   cd blond-event-calculator
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python app.py
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser.

The application creates a new local `events.db` database automatically. This database is excluded from Git so personal event and financial data are never included in the repository.

## Notes

The application is designed as a local single-user portfolio project. GitHub stores the source code, but a separate hosting service is required to provide a public live website.
