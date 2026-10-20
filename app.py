import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, url_for


app = Flask(__name__)
app.config["DATABASE"] = Path(__file__).with_name("events.db")

EXPENSE_CATEGORIES = (
    ("venue", "Venue"),
    ("artists", "Artists"),
    ("crew", "Crew"),
    ("content-media", "Content & Media"),
    ("marketing", "Marketing"),
    ("production", "Production"),
    ("rider", "Rider"),
    ("logistics", "Logistics"),
)
EXPENSE_CATEGORY_KEYS = {key for key, _ in EXPENSE_CATEGORIES}
REVENUE_TYPES = {"tickets", "other"}


def format_money(cents):
    sign = "-" if cents < 0 else ""
    return f"{sign}€{abs(cents) / 100:,.2f}"


app.jinja_env.filters["money"] = format_money


def get_database_connection():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database():
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                venue_capacity INTEGER NOT NULL CHECK (venue_capacity >= 0),
                actual_attendance INTEGER NOT NULL CHECK (actual_attendance >= 0)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS revenue_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category_type TEXT NOT NULL DEFAULT 'tickets',
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
            """
        )
        revenue_category_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(revenue_categories)")
        }
        if "category_type" not in revenue_category_columns:
            connection.execute(
                """
                ALTER TABLE revenue_categories
                ADD COLUMN category_type TEXT NOT NULL DEFAULT 'tickets'
                """
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS revenue_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (category_id) REFERENCES revenue_categories (id) ON DELETE CASCADE
            )
            """
        )


def read_non_negative_integer(value, field_name):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")

    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return number


def read_amount_in_cents(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Amount must be a valid number.")

    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    return int(amount * 100)


def get_event_snapshot(connection, event_id):
    event = connection.execute(
        """
        SELECT id, name, event_date, venue_capacity, actual_attendance
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()

    if event is None:
        return None

    expense_totals = {key: 0 for key, _ in EXPENSE_CATEGORIES}
    expense_rows = connection.execute(
        """
        SELECT category, SUM(amount_cents) AS total_cents
        FROM expense_items
        WHERE event_id = ?
        GROUP BY category
        """,
        (event_id,),
    ).fetchall()

    for row in expense_rows:
        if row["category"] in expense_totals:
            expense_totals[row["category"]] = row["total_cents"]

    revenue_row = connection.execute(
        """
        SELECT
            COALESCE(SUM(revenue_items.unit_price_cents * revenue_items.quantity), 0)
                AS total_revenue,
            COALESCE(SUM(
                CASE
                    WHEN revenue_categories.category_type = 'tickets'
                    THEN revenue_items.quantity
                    ELSE 0
                END
            ), 0) AS tickets_sold
        FROM revenue_categories
        LEFT JOIN revenue_items
            ON revenue_items.category_id = revenue_categories.id
        WHERE revenue_categories.event_id = ?
        """,
        (event_id,),
    ).fetchone()

    total_expenses = sum(expense_totals.values())
    total_revenue = revenue_row["total_revenue"]
    capacity = event["venue_capacity"]
    attendance = event["actual_attendance"]

    return {
        "event": event,
        "capacity": capacity,
        "attendance": attendance,
        "fill_rate": (attendance / capacity * 100) if capacity else None,
        "tickets_sold": revenue_row["tickets_sold"],
        "expense_totals": expense_totals,
        "total_expenses": total_expenses,
        "total_revenue": total_revenue,
        "profit": total_revenue - total_expenses,
    }


def format_comparison_value(value, value_type):
    if value is None:
        return "N/A"
    if value_type == "money":
        return format_money(value)
    if value_type == "percent":
        return f"{value:.1f}%"
    return f"{value:,}"


def format_comparison_difference(value, value_type):
    if value is None:
        return "N/A"
    if value_type == "money":
        if value > 0:
            return f"+€{value / 100:,.2f}"
        return format_money(value)
    if value_type == "percent":
        return f"{value:+.1f} pp"
    return f"{value:+,}"


def build_comparison_row(label, value_a, value_b, value_type):
    if value_a is None or value_b is None:
        difference = None
        percentage_difference = None
    else:
        difference = value_b - value_a
        percentage_difference = (
            None if value_a == 0 else difference / abs(value_a) * 100
        )

    return {
        "label": label,
        "value_a": format_comparison_value(value_a, value_type),
        "value_b": format_comparison_value(value_b, value_type),
        "difference": format_comparison_difference(difference, value_type),
        "percentage_difference": (
            "N/A"
            if percentage_difference is None
            else f"{percentage_difference:+.1f}%"
        ),
    }


@app.get("/")
def index():
    with get_database_connection() as connection:
        events = connection.execute(
            """
            SELECT id, name, event_date, venue_capacity, actual_attendance
            FROM events
            ORDER BY event_date DESC, id DESC
            """
        ).fetchall()

    return render_template("index.html", events=events)


@app.get("/compare")
def compare_events():
    with get_database_connection() as connection:
        events = connection.execute(
            """
            SELECT id, name, event_date
            FROM events
            ORDER BY event_date DESC, id DESC
            """
        ).fetchall()

        event_a_id = request.args.get("eventA", type=int)
        event_b_id = request.args.get("eventB", type=int)
        comparison_rows = []
        event_a = None
        event_b = None
        error = None

        if event_a_id is not None or event_b_id is not None:
            if event_a_id is None or event_b_id is None:
                error = "Select two events."
            elif event_a_id == event_b_id:
                error = "Select two different events."
            else:
                snapshot_a = get_event_snapshot(connection, event_a_id)
                snapshot_b = get_event_snapshot(connection, event_b_id)

                if snapshot_a is None or snapshot_b is None:
                    error = "One of the selected events was not found."
                else:
                    event_a = snapshot_a["event"]
                    event_b = snapshot_b["event"]
                    comparison_rows.extend(
                        [
                            build_comparison_row(
                                "Capacity",
                                snapshot_a["capacity"],
                                snapshot_b["capacity"],
                                "number",
                            ),
                            build_comparison_row(
                                "Attendance",
                                snapshot_a["attendance"],
                                snapshot_b["attendance"],
                                "number",
                            ),
                            build_comparison_row(
                                "Fill Rate",
                                snapshot_a["fill_rate"],
                                snapshot_b["fill_rate"],
                                "percent",
                            ),
                            build_comparison_row(
                                "Tickets Sold",
                                snapshot_a["tickets_sold"],
                                snapshot_b["tickets_sold"],
                                "number",
                            ),
                        ]
                    )

                    for category_key, category_name in EXPENSE_CATEGORIES:
                        comparison_rows.append(
                            build_comparison_row(
                                category_name,
                                snapshot_a["expense_totals"][category_key],
                                snapshot_b["expense_totals"][category_key],
                                "money",
                            )
                        )

                    comparison_rows.extend(
                        [
                            build_comparison_row(
                                "Total Expenses",
                                snapshot_a["total_expenses"],
                                snapshot_b["total_expenses"],
                                "money",
                            ),
                            build_comparison_row(
                                "Total Revenue",
                                snapshot_a["total_revenue"],
                                snapshot_b["total_revenue"],
                                "money",
                            ),
                            build_comparison_row(
                                "Profit / Loss",
                                snapshot_a["profit"],
                                snapshot_b["profit"],
                                "money",
                            ),
                        ]
                    )

    return render_template(
        "compare.html",
        events=events,
        selected_event_a=event_a_id,
        selected_event_b=event_b_id,
        event_a=event_a,
        event_b=event_b,
        comparison_rows=comparison_rows,
        error=error,
    )


@app.get("/events/<int:event_id>")
def event_detail(event_id):
    with get_database_connection() as connection:
        event = connection.execute(
            """
            SELECT id, name, event_date, venue_capacity, actual_attendance
            FROM events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

        if event is None:
            abort(404)

        expense_rows = connection.execute(
            """
            SELECT id, category, name, amount_cents, notes
            FROM expense_items
            WHERE event_id = ?
            ORDER BY id
            """,
            (event_id,),
        ).fetchall()
        revenue_category_rows = connection.execute(
            """
            SELECT id, name, category_type
            FROM revenue_categories
            WHERE event_id = ?
            ORDER BY id
            """,
            (event_id,),
        ).fetchall()
        revenue_item_rows = connection.execute(
            """
            SELECT
                revenue_items.id,
                revenue_items.category_id,
                revenue_items.name,
                revenue_items.unit_price_cents,
                revenue_items.quantity,
                revenue_items.notes
            FROM revenue_items
            JOIN revenue_categories
                ON revenue_categories.id = revenue_items.category_id
            WHERE revenue_categories.event_id = ?
            ORDER BY revenue_items.id
            """,
            (event_id,),
        ).fetchall()

    items_by_category = {key: [] for key, _ in EXPENSE_CATEGORIES}
    category_totals = {key: 0 for key, _ in EXPENSE_CATEGORIES}

    for item in expense_rows:
        if item["category"] in items_by_category:
            items_by_category[item["category"]].append(item)
            category_totals[item["category"]] += item["amount_cents"]

    revenue_categories = []
    revenue_categories_by_id = {}

    for category in revenue_category_rows:
        category_data = {
            "id": category["id"],
            "name": category["name"],
            "category_type": category["category_type"],
            "items": [],
            "total_cents": 0,
        }
        revenue_categories.append(category_data)
        revenue_categories_by_id[category["id"]] = category_data

    for item in revenue_item_rows:
        category_data = revenue_categories_by_id[item["category_id"]]
        line_total_cents = item["unit_price_cents"] * item["quantity"]
        category_data["items"].append(
            {
                "id": item["id"],
                "name": item["name"],
                "unit_price_cents": item["unit_price_cents"],
                "quantity": item["quantity"],
                "notes": item["notes"],
                "line_total_cents": line_total_cents,
            }
        )
        category_data["total_cents"] += line_total_cents

    total_expenses = sum(category_totals.values())
    total_revenue = sum(category["total_cents"] for category in revenue_categories)
    total_tickets_sold = sum(
        item["quantity"]
        for category in revenue_categories
        if category["category_type"] == "tickets"
        for item in category["items"]
    )

    return render_template(
        "event.html",
        event=event,
        expense_categories=EXPENSE_CATEGORIES,
        items_by_category=items_by_category,
        category_totals=category_totals,
        total_expenses=total_expenses,
        revenue_categories=revenue_categories,
        total_revenue=total_revenue,
        total_tickets_sold=total_tickets_sold,
        profit=total_revenue - total_expenses,
    )


@app.post("/api/events")
def create_event():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    event_date = str(data.get("eventDate", "")).strip()

    if not name:
        return jsonify({"error": "Event name is required."}), 400

    if not event_date:
        return jsonify({"error": "Event date is required."}), 400

    try:
        venue_capacity = read_non_negative_integer(
            data.get("venueCapacity"), "Venue capacity"
        )
        actual_attendance = read_non_negative_integer(
            data.get("actualAttendance"), "Actual attendance"
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (name, event_date, venue_capacity, actual_attendance)
            VALUES (?, ?, ?, ?)
            """,
            (name, event_date, venue_capacity, actual_attendance),
        )

    return (
        jsonify(
            {
                "event": {
                    "id": cursor.lastrowid,
                    "name": name,
                    "eventDate": event_date,
                    "venueCapacity": venue_capacity,
                    "actualAttendance": actual_attendance,
                    "url": url_for("event_detail", event_id=cursor.lastrowid),
                }
            }
        ),
        201,
    )


@app.patch("/api/events/<int:event_id>")
def update_event(event_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    event_date = str(data.get("eventDate", "")).strip()

    if not name:
        return jsonify({"error": "Event name is required."}), 400

    if not event_date:
        return jsonify({"error": "Event date is required."}), 400

    try:
        venue_capacity = read_non_negative_integer(
            data.get("venueCapacity"), "Venue capacity"
        )
        actual_attendance = read_non_negative_integer(
            data.get("actualAttendance"), "Actual attendance"
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE events
            SET name = ?, event_date = ?, venue_capacity = ?, actual_attendance = ?
            WHERE id = ?
            """,
            (name, event_date, venue_capacity, actual_attendance, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Event not found."}), 404

    return jsonify({"message": "Event updated."})


@app.delete("/api/events/<int:event_id>")
def delete_event(event_id):
    with get_database_connection() as connection:
        cursor = connection.execute("DELETE FROM events WHERE id = ?", (event_id,))

        if cursor.rowcount == 0:
            return jsonify({"error": "Event not found."}), 404

    return "", 204


@app.post("/api/events/<int:event_id>/expenses")
def create_expense_item(event_id):
    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if category not in EXPENSE_CATEGORY_KEYS:
        return jsonify({"error": "Invalid expense category."}), 400

    if not name:
        return jsonify({"error": "Item name is required."}), 400

    try:
        amount_cents = read_amount_in_cents(data.get("amount"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        event_exists = connection.execute(
            "SELECT 1 FROM events WHERE id = ?", (event_id,)
        ).fetchone()

        if event_exists is None:
            return jsonify({"error": "Event not found."}), 404

        cursor = connection.execute(
            """
            INSERT INTO expense_items (event_id, category, name, amount_cents, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, category, name, amount_cents, notes),
        )

    return jsonify({"itemId": cursor.lastrowid}), 201


@app.patch("/api/events/<int:event_id>/expenses/<int:item_id>")
def update_expense_item(event_id, item_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name:
        return jsonify({"error": "Item name is required."}), 400

    try:
        amount_cents = read_amount_in_cents(data.get("amount"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE expense_items
            SET name = ?, amount_cents = ?, notes = ?
            WHERE id = ? AND event_id = ?
            """,
            (name, amount_cents, notes, item_id, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Expense item not found."}), 404

    return jsonify({"message": "Expense item updated."})


@app.delete("/api/events/<int:event_id>/expenses/<int:item_id>")
def delete_expense_item(event_id, item_id):
    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM expense_items
            WHERE id = ? AND event_id = ?
            """,
            (item_id, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Expense item not found."}), 404

    return "", 204


@app.post("/api/events/<int:event_id>/revenue-categories")
def create_revenue_category(event_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    category_type = str(data.get("categoryType", "")).strip()

    if not name:
        return jsonify({"error": "Category name is required."}), 400

    if category_type not in REVENUE_TYPES:
        return jsonify({"error": "Invalid revenue category type."}), 400

    with get_database_connection() as connection:
        event_exists = connection.execute(
            "SELECT 1 FROM events WHERE id = ?", (event_id,)
        ).fetchone()

        if event_exists is None:
            return jsonify({"error": "Event not found."}), 404

        cursor = connection.execute(
            """
            INSERT INTO revenue_categories (event_id, name, category_type)
            VALUES (?, ?, ?)
            """,
            (event_id, name, category_type),
        )

    return jsonify({"categoryId": cursor.lastrowid}), 201


@app.patch("/api/events/<int:event_id>/revenue-categories/<int:category_id>")
def update_revenue_category(event_id, category_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    category_type = str(data.get("categoryType", "")).strip()

    if not name:
        return jsonify({"error": "Category name is required."}), 400

    if category_type not in REVENUE_TYPES:
        return jsonify({"error": "Invalid revenue category type."}), 400

    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE revenue_categories
            SET name = ?, category_type = ?
            WHERE id = ? AND event_id = ?
            """,
            (name, category_type, category_id, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Revenue category not found."}), 404

    return jsonify({"message": "Revenue category updated."})


@app.delete("/api/events/<int:event_id>/revenue-categories/<int:category_id>")
def delete_revenue_category(event_id, category_id):
    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM revenue_categories
            WHERE id = ? AND event_id = ?
            """,
            (category_id, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Revenue category not found."}), 404

    return "", 204


@app.post("/api/events/<int:event_id>/revenue-categories/<int:category_id>/items")
def create_revenue_item(event_id, category_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name:
        return jsonify({"error": "Item name is required."}), 400

    try:
        unit_price_cents = read_amount_in_cents(data.get("unitPrice"))
        quantity = read_non_negative_integer(data.get("quantity"), "Quantity")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        category_exists = connection.execute(
            """
            SELECT 1
            FROM revenue_categories
            WHERE id = ? AND event_id = ?
            """,
            (category_id, event_id),
        ).fetchone()

        if category_exists is None:
            return jsonify({"error": "Revenue category not found."}), 404

        cursor = connection.execute(
            """
            INSERT INTO revenue_items (
                category_id, name, unit_price_cents, quantity, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (category_id, name, unit_price_cents, quantity, notes),
        )

    return jsonify({"itemId": cursor.lastrowid}), 201


@app.patch(
    "/api/events/<int:event_id>/revenue-categories/<int:category_id>/items/<int:item_id>"
)
def update_revenue_item(event_id, category_id, item_id):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name:
        return jsonify({"error": "Item name is required."}), 400

    try:
        unit_price_cents = read_amount_in_cents(data.get("unitPrice"))
        quantity = read_non_negative_integer(data.get("quantity"), "Quantity")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE revenue_items
            SET name = ?, unit_price_cents = ?, quantity = ?, notes = ?
            WHERE id = ?
              AND category_id = ?
              AND EXISTS (
                  SELECT 1
                  FROM revenue_categories
                  WHERE id = ? AND event_id = ?
              )
            """,
            (
                name,
                unit_price_cents,
                quantity,
                notes,
                item_id,
                category_id,
                category_id,
                event_id,
            ),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Revenue item not found."}), 404

    return jsonify({"message": "Revenue item updated."})


@app.delete(
    "/api/events/<int:event_id>/revenue-categories/<int:category_id>/items/<int:item_id>"
)
def delete_revenue_item(event_id, category_id, item_id):
    with get_database_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM revenue_items
            WHERE id = ?
              AND category_id = ?
              AND EXISTS (
                  SELECT 1
                  FROM revenue_categories
                  WHERE id = ? AND event_id = ?
              )
            """,
            (item_id, category_id, category_id, event_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Revenue item not found."}), 404

    return "", 204


with app.app_context():
    initialise_database()


if __name__ == "__main__":
    app.run(debug=True)
