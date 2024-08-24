import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, DATABASE_URL
from main import app, get_db
import models

# Setup test database
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="function")
def test_book():
    """Fixture to create and return a test book, with cleanup after each test."""
    db = TestingSessionLocal()
    new_book = models.Book(title="Test Book", author="Test Author", description="Test Description", rating=5)
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    yield new_book  # Provide the test with the created book
    db.delete(new_book)
    db.commit()
    db.close()

@pytest.fixture(scope="function", autouse=True)
def clean_database():
    """Fixture to clean up the database before and after each test."""
    db = TestingSessionLocal()
    db.query(models.Book).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(models.Book).delete()
    db.commit()
    db.close()

# Test cases
def test_get_books_returns_empty_list():
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == []

def test_get_books_returns_list_of_books(test_book):
    response = client.get("/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["title"] == test_book.title

def test_get_book_by_id(test_book):
    response = client.get(f"/books/{test_book.id}")
    assert response.status_code == 200
    assert response.json()["title"] == test_book.title

def test_get_book_returns_404_for_nonexistent_book():
    response = client.get("/books/999")
    assert response.status_code == 404

def test_create_book():
    book_data = {"title": "New Book", "author": "New Author", "description": "New Description", "rating": 4}
    response = client.post("/books", json=book_data)
    assert response.status_code == 200
    created_book = response.json()
    assert created_book["title"] == book_data["title"]

def test_update_book(test_book):
    updated_data = {"title": "Updated Book", "author": "Updated Author", "description": "Updated Description", "rating": 3}
    response = client.put(f"/books/{test_book.id}", json=updated_data)
    assert response.status_code == 200
    updated_book = response.json()
    assert updated_book["title"] == updated_data["title"]

def test_update_book_returns_404_for_nonexistent_book():
    updated_data = {"title": "Updated Book", "author": "Updated Author", "description": "Updated Description", "rating": 3}
    response = client.put("/books/999", json=updated_data)
    assert response.status_code == 404

def test_delete_book(test_book):
    response = client.delete(f"/books/{test_book.id}")
    assert response.status_code == 200
    assert client.get(f"/books/{test_book.id}").status_code == 404

def test_delete_book_returns_404_for_nonexistent_book():
    response = client.delete("/books/999")
    assert response.status_code == 404

def test_delete_all_books(test_book):
    response = client.delete("/books")
    assert response.status_code == 200
    assert client.get("/books").json() == []
