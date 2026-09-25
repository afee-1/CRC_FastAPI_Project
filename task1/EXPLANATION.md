# Task 1 — Application Logic Explanation

## 1. How the SQLite database is created using `create_engine()`

```python
DATABASE_URL = "sqlite:///./lost_found.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True
)
```

`create_engine()` from SQLModel (which wraps SQLAlchemy) establishes a connection
pool to the SQLite file `lost_found.db` in the project directory. The file is
created automatically if it doesn't exist.

- `connect_args={"check_same_thread": False}` — SQLite by default only allows one
  thread to use a connection. Since FastAPI is async and can handle multiple requests
  on different threads, this flag disables that restriction safely.
- `echo=True` — prints every SQL statement to the console for debugging.

At startup, `SQLModel.metadata.create_all(engine)` inspects all `table=True` models
and issues `CREATE TABLE IF NOT EXISTS` statements for each one.

---

## 2. How SQLModel is used to store and retrieve items

**Storing (POST /items):**
```python
db_item = Item.model_validate(item_in)   # Pydantic validates the input
session.add(db_item)                      # Stage the INSERT
session.commit()                          # Flush to SQLite
session.refresh(db_item)                  # Reload to get the auto-generated id
```

**Retrieving (GET /items):**
```python
items = session.exec(select(Item)).all()
```
`select(Item)` generates `SELECT * FROM item`. `session.exec()` runs it against
the database and `.all()` returns a Python list of `Item` objects.

**Session lifecycle** is managed via the `get_session()` dependency:
```python
def get_session():
    with Session(engine) as session:
        yield session
```
FastAPI calls `next()` before the route and `close()` after — ensuring every
request gets its own session that is always cleaned up.

---

## 3. How status/category filtering is implemented

Filtering uses SQLModel's `select().where()` to push the filter condition into SQL,
avoiding loading the entire table into Python first:

```python
# Status filter
items = session.exec(
    select(Item).where(Item.status == status)
).all()

# Category filter
items = session.exec(
    select(Item).where(Item.category == category)
).all()
```

Both `status` and `category` are path parameters typed as Python `Enum` subclasses
(`ItemStatus`, `ItemCategory`). FastAPI automatically validates that the path value
matches one of the enum members before the function body runs — invalid values return
HTTP 422 Unprocessable Entity automatically.

---

## 4. How the API handles a non-existing item ID

A helper function `get_item_or_404()` is used by every route that needs an item:

```python
def get_item_or_404(item_id: int, session: Session) -> Item:
    item = session.get(Item, item_id)   # SELECT by primary key
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Item with id={item_id} not found."
        )
    return item
```

`session.get(Item, item_id)` issues `SELECT * FROM item WHERE id = ?`. If SQLite
returns no row, it returns `None`. The `if not item` check raises `HTTPException`
with a 404 status code and a human-readable message. FastAPI converts this into a
JSON response:

```json
{
  "detail": "Item with id=99 not found."
}
```

---

## 5. How validation prevents invalid status values

Status validation works at two levels:

**Level 1 — Python Enum:**
```python
class ItemStatus(str, Enum):
    lost     = "Lost"
    found    = "Found"
    returned = "Returned"
```
The `status` field in `ItemBase` is typed as `ItemStatus`. Pydantic (used by
SQLModel) will reject any string that is not one of `"Lost"`, `"Found"`,
`"Returned"` with a 422 error before the route body even executes.

**Level 2 — Path parameter validation:**
For `GET /items/status/{status}`, the path parameter is also typed as `ItemStatus`.
If someone calls `/items/status/Stolen`, FastAPI returns:

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["path", "status"],
      "msg": "Input should be 'Lost', 'Found' or 'Returned'",
      "input": "Stolen"
    }
  ]
}
```

This means invalid status values are **never** stored in the database and
**never** reach the filtering query.
