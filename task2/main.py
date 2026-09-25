"""
Task 2 — Event Reservation Management System API
FastAPI application using SQLite + SQLModel
"""

from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import EmailStr
from sqlmodel import Field, Session, SQLModel, create_engine, select, func


# ─── Enums ───────────────────────────────────────────────────────────────────

class EventStatus(str, Enum):
    open = "Open"
    closed = "Closed"


# ─── SQLModel Database Models ────────────────────────────────────────────────

class EventBase(SQLModel):
    title:     str         = Field(min_length=1, max_length=200, description="Event name")
    venue:     str         = Field(min_length=1, max_length=200, description="Event location")
    capacity:  int         = Field(gt=0, description="Maximum number of participants (must be > 0)")
    organizer: str         = Field(min_length=1, max_length=100, description="Organizer name")
    status:    EventStatus = Field(default=EventStatus.open, description="Open or Closed")


class Event(EventBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class EventCreate(EventBase):
    pass


class EventUpdate(SQLModel):
    title:     Optional[str]         = Field(default=None, min_length=1, max_length=200)
    venue:     Optional[str]         = Field(default=None, min_length=1, max_length=200)
    capacity:  Optional[int]         = Field(default=None, gt=0)
    organizer: Optional[str]         = Field(default=None, min_length=1, max_length=100)
    status:    Optional[EventStatus] = None


class EventRead(EventBase):
    id: int


# ── Reservation Models ────────────────────────────────────────────────────────

class ReservationBase(SQLModel):
    student_name: str      = Field(min_length=1, max_length=100, description="Name of participant")
    roll_number:  str      = Field(min_length=1, max_length=30, description="Participant roll number")
    email:        EmailStr = Field(description="Validated participant email address")


class Reservation(ReservationBase, table=True):
    id:       Optional[int] = Field(default=None, primary_key=True)
    event_id: int           = Field(foreign_key="event.id", description="ID of the associated event")


class ReservationCreate(ReservationBase):
    pass


class ReservationRead(ReservationBase):
    id:       int
    event_id: int


class EventAvailability(SQLModel):
    event_id:  int
    title:     str
    capacity:  int
    booked:    int
    remaining: int


# ─── Database Setup ───────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./events.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# ─── FastAPI Application Setup ────────────────────────────────────────────────

app = FastAPI(
    title="Event Reservation Management System API",
    description="REST API for managing college events and student reservations with strict capacity control.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_event_or_404(event_id: int, session: Session) -> Event:
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id={event_id} not found."
        )
    return event


def get_booked_count(event_id: int, session: Session) -> int:
    statement = select(func.count(Reservation.id)).where(Reservation.event_id == event_id)
    return session.exec(statement).one()


# ─── REQUIRED EVENT APIs ──────────────────────────────────────────────────────

@app.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED, tags=["Events"])
def create_event(event_in: EventCreate, session: Session = Depends(get_session)):
    """1. Create a new event."""
    db_event = Event.model_validate(event_in)
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


@app.get("/events", response_model=List[EventRead], tags=["Events"])
def list_events(session: Session = Depends(get_session)):
    """2. Return all events."""
    return session.exec(select(Event)).all()


@app.get("/events/{event_id}", response_model=EventRead, tags=["Events"])
def get_event(event_id: int, session: Session = Depends(get_session)):
    """3. Return a specific event by ID."""
    return get_event_or_404(event_id, session)


@app.put("/events/{event_id}", response_model=EventRead, tags=["Events"])
def update_event(event_id: int, event_in: EventUpdate, session: Session = Depends(get_session)):
    """4. Update event information."""
    db_event = get_event_or_404(event_id, session)
    update_data = event_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_event, key, value)
        
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


@app.delete("/events/{event_id}", status_code=status.HTTP_200_OK, tags=["Events"])
def delete_event(event_id: int, session: Session = Depends(get_session)):
    """5. Delete an event and all associated reservations."""
    db_event = get_event_or_404(event_id, session)

    # Delete all associated reservations for this event
    reservations = session.exec(select(Reservation).where(Reservation.event_id == event_id)).all()
    for res in reservations:
        session.delete(res)

    session.delete(db_event)
    session.commit()
    return {"message": f"Event {event_id} and all its reservations have been deleted."}


# ─── REQUIRED RESERVATION APIs ────────────────────────────────────────────────

@app.post("/events/{event_id}/reserve", response_model=ReservationRead, status_code=status.HTTP_201_CREATED, tags=["Reservations"])
def create_reservation(event_id: int, res_in: ReservationCreate, session: Session = Depends(get_session)):
    """
    6. Create a reservation for an event.
    Verifies event existence, 'Open' status, and available capacity.
    """
    # 1. Verify that the event exists
    event = get_event_or_404(event_id, session)

    # 2. Verify that the event is Open
    if event.status != EventStatus.open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reserve: Event '{event.title}' is currently Closed."
        )

    # 3. Check existing reservations and prevent exceeding capacity
    booked_count = get_booked_count(event_id, session)
    if booked_count >= event.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reserve: Event '{event.title}' has reached maximum capacity ({event.capacity}/{event.capacity})."
        )

    # 4. Create and persist reservation
    db_reservation = Reservation(
        event_id=event_id,
        student_name=res_in.student_name,
        roll_number=res_in.roll_number,
        email=res_in.email
    )
    session.add(db_reservation)
    session.commit()
    session.refresh(db_reservation)
    return db_reservation


@app.get("/events/{event_id}/reservations", response_model=List[ReservationRead], tags=["Reservations"])
def list_event_reservations(event_id: int, session: Session = Depends(get_session)):
    """7. Return all reservations for a particular event."""
    get_event_or_404(event_id, session)
    return session.exec(select(Reservation).where(Reservation.event_id == event_id)).all()


@app.delete("/reservations/{reservation_id}", status_code=status.HTTP_200_OK, tags=["Reservations"])
def cancel_reservation(reservation_id: int, session: Session = Depends(get_session)):
    """8. Cancel a reservation."""
    db_reservation = session.get(Reservation, reservation_id)
    if not db_reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with id={reservation_id} not found."
        )

    session.delete(db_reservation)
    session.commit()
    return {"message": f"Reservation {reservation_id} canceled successfully."}


@app.get("/events/{event_id}/availability", response_model=EventAvailability, tags=["Reservations"])
def get_event_availability(event_id: int, session: Session = Depends(get_session)):
    """9. Return total seats, booked seats, and remaining seats for an event."""
    event = get_event_or_404(event_id, session)
    booked = get_booked_count(event_id, session)
    remaining = max(0, event.capacity - booked)

    return EventAvailability(
        event_id=event_id,
        title=event.title,
        capacity=event.capacity,
        booked=booked,
        remaining=remaining
    )