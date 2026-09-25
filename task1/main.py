"""
Task 1 — Campus Lost & Found API
FastAPI application using SQLite + SQLModel
"""

from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select


# ─── Enums ───────────────────────────────────────────────────────────────────

class ItemStatus(str, Enum):
    lost     = "Lost"
    found    = "Found"
    returned = "Returned"


class ItemCategory(str, Enum):
    electronics  = "Electronics"
    documents    = "Documents"
    accessories  = "Accessories"
    clothing     = "Clothing"
    books        = "Books"
    keys         = "Keys"
    bags         = "Bags"
    other        = "Other"


# ─── Models ──────────────────────────────────────────────────────────────────

class ItemBase(SQLModel):
    """Shared fields used for both create and update."""
    title:        str         = Field(min_length=1, max_length=200,  description="Name/title of the item")
    description:  str         = Field(min_length=5, max_length=1000, description="Description of the item")
    category:     ItemCategory                                        = Field(description="Category of the item")
    location:     str         = Field(min_length=1, max_length=200,  description="Location where item was lost/found")
    reported_by:  str         = Field(min_length=1, max_length=100,  description="Name of the person reporting")
    status:       ItemStatus  = Field(default=ItemStatus.lost,        description="Status: Lost, Found, or Returned")


class Item(ItemBase, table=True):
    """Database table model."""
    id: Optional[int] = Field(default=None, primary_key=True)


class ItemCreate(ItemBase):
    """Request body for POST /items."""
    pass


class ItemUpdate(SQLModel):
    """Request body for PUT /items/{item_id} — all fields optional."""
    title:       Optional[str]          = Field(default=None, min_length=1, max_length=200)
    description: Optional[str]          = Field(default=None, min_length=5, max_length=1000)
    category:    Optional[ItemCategory] = None
    location:    Optional[str]          = Field(default=None, min_length=1, max_length=200)
    reported_by: Optional[str]          = Field(default=None, min_length=1, max_length=100)
    status:      Optional[ItemStatus]   = None


class ItemRead(ItemBase):
    """Response model — includes the auto-generated id."""
    id: int


# ─── Database Setup ───────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./lost_found.db"

# create_engine() sets up the connection to the SQLite file.
# connect_args={"check_same_thread": False} is required for SQLite with FastAPI
# because FastAPI can handle requests on different threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)


def create_db_and_tables():
    """Called on startup — creates the 'item' table if it doesn't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency — yields a database session per request, then closes it."""
    with Session(engine) as session:
        yield session


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Campus Lost & Found API",
    description="A REST API for reporting and managing lost/found items on campus.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# ─── Helper ───────────────────────────────────────────────────────────────────

def get_item_or_404(item_id: int, session: Session) -> Item:
    """Fetch an item by ID, raise 404 if not found."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Item with id={item_id} not found."
        )
    return item


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post("/items", response_model=ItemRead, status_code=201, tags=["Items"])
def create_item(item_in: ItemCreate, session: Session = Depends(get_session)):
    """
    Create a new lost/found item report.
    - title must not be empty
    - description must be at least 5 characters
    - status must be Lost, Found, or Returned
    """
    db_item = Item.model_validate(item_in)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.get("/items", response_model=List[ItemRead], tags=["Items"])
def list_items(session: Session = Depends(get_session)):
    """Return all reported items."""
    items = session.exec(select(Item)).all()
    return items


@app.get("/items/status/{status}", response_model=List[ItemRead], tags=["Items"])
def get_items_by_status(status: ItemStatus, session: Session = Depends(get_session)):
    """
    Return items filtered by status.
    Example: GET /items/status/Lost
    """
    items = session.exec(select(Item).where(Item.status == status)).all()
    return items


@app.get("/items/category/{category}", response_model=List[ItemRead], tags=["Items"])
def get_items_by_category(category: ItemCategory, session: Session = Depends(get_session)):
    """
    Return items filtered by category.
    Example: GET /items/category/Electronics
    """
    items = session.exec(select(Item).where(Item.category == category)).all()
    return items


@app.get("/items/{item_id}", response_model=ItemRead, tags=["Items"])
def get_item(item_id: int, session: Session = Depends(get_session)):
    """
    Return a specific item by ID.
    Returns 404 if the item does not exist.
    """
    return get_item_or_404(item_id, session)


@app.put("/items/{item_id}", response_model=ItemRead, tags=["Items"])
def update_item(
    item_id: int,
    item_in: ItemUpdate,
    session: Session = Depends(get_session),
):
    """
    Update the details or status of an existing item.
    Only the provided fields are updated (partial update).
    """
    db_item = get_item_or_404(item_id, session)

    # Apply only the fields that were explicitly sent in the request
    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}", status_code=200, tags=["Items"])
def delete_item(item_id: int, session: Session = Depends(get_session)):
    """
    Delete an item report by ID.
    Returns 404 if the item does not exist.
    """
    db_item = get_item_or_404(item_id, session)
    session.delete(db_item)
    session.commit()
    return {"message": f"Item {item_id} deleted successfully."}
