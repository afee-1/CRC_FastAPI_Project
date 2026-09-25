# FastAPI Practical Assessment

Two fully working FastAPI applications built with **SQLite + SQLModel**.

---

## Repository Structure

```
fastapi-assessment/
├── task1/                  # Campus Lost & Found API
│   ├── main.py
│   └── requirements.txt
├── task2/                  # Student Attendance Tracker API
│   ├── main.py
│   └── requirements.txt
├── screenshots/            # Proof-of-work screenshots
└── README.md
```

---

## Prerequisites

- Python 3.10 or higher
- pip

---

## Task 1 — Campus Lost & Found API

### Setup & Run

```bash
# 1. Navigate to task1 folder
cd task1

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the server
uvicorn main:app --reload --port 8000
```

### Swagger UI
Open your browser at:
```
http://127.0.0.1:8000/docs
```

### API Endpoints

| Method | Endpoint                         | Description                          |
|--------|----------------------------------|--------------------------------------|
| POST   | `/items`                         | Create a new lost/found item         |
| GET    | `/items`                         | Return all items                     |
| GET    | `/items/{item_id}`               | Return a specific item by ID         |
| PUT    | `/items/{item_id}`               | Update an existing item              |
| DELETE | `/items/{item_id}`               | Delete an item report                |
| GET    | `/items/status/{status}`         | Filter by status (Lost/Found/Returned)|
| GET    | `/items/category/{category}`     | Filter by category                   |

### Example Request — POST /items

```json
{
  "title": "Black Laptop Bag",
  "description": "Dell laptop bag with charger inside, found near library entrance",
  "category": "Bags",
  "location": "Main Library",
  "reported_by": "Rahul Sharma",
  "status": "Found"
}
```

### Valid Status Values
`Lost` | `Found` | `Returned`

### Valid Category Values
`Electronics` | `Documents` | `Accessories` | `Clothing` | `Books` | `Keys` | `Bags` | `Other`

---
## Task 2 — Campus Event Seat Reservation API

### Setup & Run

```bash
# 1. Navigate to task2 folder
cd task2

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the server
uvicorn main:app --reload --port 8001
```

### Swagger UI

Open your browser at:

```text
http://127.0.0.1:8001/docs
```

### Database

- Database: SQLite
- ORM/Database library: SQLModel
- Database engine is created using `create_engine()`.
- Required tables are automatically created when the application starts.
- The Task 2 database file is created automatically on first run.

### Event Model

The `Event` model contains:

| Field | Description |
|---|---|
| `id` | Integer primary key |
| `title` | Event name |
| `venue` | Event location |
| `capacity` | Maximum number of participants |
| `organizer` | Organizer name |
| `status` | Event status — Open or Closed |

### Reservation Model

The `Reservation` model contains:

| Field | Description |
|---|---|
| `id` | Integer primary key |
| `event_id` | ID of the event |
| `student_name` | Name of participant |
| `roll_number` | Participant roll number |
| `email` | Participant email |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/events` | Create a new event |
| GET | `/events` | Return all events |
| GET | `/events/{event_id}` | Return a specific event |
| PUT | `/events/{event_id}` | Update event information |
| DELETE | `/events/{event_id}` | Delete an event |
| POST | `/events/{event_id}/reserve` | Create a reservation for an event |
| GET | `/events/{event_id}/reservations` | Return all reservations for an event |
| DELETE | `/reservations/{reservation_id}` | Cancel a reservation |
| GET | `/events/{event_id}/availability` | Return total, booked and remaining seats |

### Example Request — POST /events

```json
{
  "title": "Tech Hackathon 2026",
  "venue": "College Auditorium",
  "capacity": 50,
  "organizer": "Computer Science Department",
  "status": "Open"
}
```

### Example Request — POST /events/{event_id}/reserve

```json
{
  "student_name": "Priya Mehta",
  "roll_number": "CS2024001",
  "email": "priya.mehta@college.edu"
}
```

### Example Response — GET /events/{event_id}/availability

```json
{
  "capacity": 50,
  "booked": 32,
  "remaining": 18
}
```

### Reservation Business Logic

Before creating a reservation, the API:

1. Verifies that the event exists.
2. Verifies that the event status is `Open`.
3. Checks the number of existing reservations.
4. Prevents reservations when the event is already full.
5. Ensures that an event cannot exceed its defined capacity.

For example, if an event has a capacity of `30` and already has `30` reservations, the next reservation request is rejected with an appropriate HTTP error.

Reservations are also rejected when an event has been marked as `Closed`.

### Validation

- Event capacity must be greater than `0`.
- Student name must not be empty.
- Email must be a valid email address.
- Every reservation must reference an existing event.
- Invalid request data returns HTTP `422`.
- Missing records return HTTP `404` with a descriptive error message.

### Proof of Work

The `screenshots/` folder should contain screenshots demonstrating:

- POST `/events`
- GET `/events`
- Successful reservation creation
- GET event reservations
- Event availability
- Successful reservation cancellation
- An unsuccessful reservation when the event is full **or** closed

The screenshots should clearly demonstrate that the reservation and seat-capacity business logic is working correctly.