"""
This module contains FastAPI routes for Home page
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home():
    """Home page route."""
    return """
    <html>
        <head>
            <title>Last Mile Health - Senior Full-Stack Engineer, AI & Digital Health</title>
        </head>
        <body>
            <h1>Welcome to the Last Mile Health Senior Full-Stack Engineer, AI & Digital Health Practice Interview!</h1>
            <p>This is the home page for the practice interview.</p>
            <ul>
                <li>Exercise 1: Basic API Endpoint</li>
                <li>Exercise 2: Database Interaction</li>
                <li>Exercise 3: AI Integration</li>
            </ul>
        </body>
    </html>
    """