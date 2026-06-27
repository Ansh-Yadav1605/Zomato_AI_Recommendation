"""
restaurant.py — Restaurant data model.

Defines the Restaurant Pydantic model representing a single restaurant
entity from the Zomato dataset after preprocessing.
"""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import Optional


class Restaurant(BaseModel):
    """
    Represents a single restaurant from the processed Zomato dataset.

    All fields correspond to the cleaned, normalized output from the
    preprocessor — not the raw Hugging Face column names.

    Attributes:
        name:                Name of the restaurant.
        url:                 Zomato page URL.
        address:             Full street address.
        location:            Locality / neighbourhood (e.g., "Koramangala").
        city:                City the restaurant is listed in.
        cuisines:            Comma-separated cuisine types (e.g., "Italian, Chinese").
        average_cost:        Approximate cost for two people (₹).
        rating:              Aggregated user rating (0.0–5.0, or 0.0 if unrated).
        votes:               Number of user votes / reviews.
        online_order:        Whether the restaurant accepts online orders.
        book_table:          Whether table booking is available.
        rest_type:           Type of restaurant (e.g., "Casual Dining", "Café").
        dish_liked:          Popular / frequently liked dishes.
        menu_item:           Representative menu items.
        listed_in_type:      Listing category (e.g., "Buffet", "Delivery").
    """

    name: str
    url: Optional[str] = None
    address: Optional[str] = None
    location: str
    city: Optional[str] = None
    cuisines: str = ""
    average_cost: float = 0.0
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    votes: int = 0
    online_order: bool = False
    book_table: bool = False
    rest_type: Optional[str] = None
    dish_liked: Optional[str] = None
    menu_item: Optional[str] = None
    listed_in_type: Optional[str] = None

    class Config:
        frozen = False
        str_strip_whitespace = True
