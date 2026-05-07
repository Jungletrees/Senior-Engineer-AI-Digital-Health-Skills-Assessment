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
            <title>Last Mile Health - Senior Full-Stack Engineer, AI &amp; Digital Health Practice Assessment</title>
            <style>
                body { font-family: Georgia, 'Times New Roman', serif; max-width: 860px; margin: 48px auto; padding: 0 24px; color: #1a1a1a; line-height: 1.7; }
                h1 { font-size: 1.6rem; font-weight: 700; border-bottom: 2px solid #c8102e; padding-bottom: 12px; margin-bottom: 8px; }
                h2 { font-size: 1.15rem; font-weight: 700; margin-top: 32px; margin-bottom: 8px; color: #c8102e; text-transform: uppercase; letter-spacing: 0.05em; }
                h3 { font-size: 1rem; font-weight: 700; margin-top: 20px; margin-bottom: 4px; }
                p.subtitle { color: #555; font-size: 0.95rem; margin-top: 4px; }
                ul { padding-left: 20px; margin: 8px 0; }
                li { margin-bottom: 6px; }
                .stack-table { border-collapse: collapse; width: 100%; margin: 12px 0; }
                .stack-table th, .stack-table td { text-align: left; padding: 8px 12px; border: 1px solid #ddd; font-size: 0.93rem; }
                .stack-table th { background: #f5f5f5; font-weight: 700; }
                .bonus { background: #fff8e1; border-left: 4px solid #f5a623; padding: 12px 16px; border-radius: 2px; margin-top: 28px; }
                .bonus h2 { color: #b7791f; margin-top: 0; }
            </style>
        </head>
        <body>
            <h1>Last Mile Health &mdash; Senior Full-Stack Engineer, AI &amp; Digital Health Practice Assessment</h1>
            <p class="subtitle">Thank you for taking the time to complete this assessment. Please read the requirements carefully before you begin.</p>

            <h2>Project Overview</h2>
            <p>You are tasked with building a <strong>Retrieval-Augmented Generation (RAG)</strong> application using the provided starter code. Your solution should demonstrate production-quality thinking across the full stack.</p>

            <table class="stack-table">
                <tr><th>Layer</th><th>Provided Starter</th><th>Substitution Policy</th></tr>
                <tr><td>Frontend</td><td>Next.js (React)</td><td>Any framework you prefer; Chainlit is also acceptable for the chat interface.</td></tr>
                <tr><td>Backend</td><td>FastAPI (Python)</td><td>Substitute with a framework you are more comfortable with, provided core requirements are met.</td></tr>
                <tr><td>Database</td><td>PostgreSQL</td><td>Required; do not substitute.</td></tr>
            </table>

            <h2>Requirements</h2>

            <h3>1. Chat Interface</h3>
            <ul>
                <li>A user-friendly chat UI for interacting with the RAG system.</li>
                <li>Responses should be grounded in the content of uploaded documents.</li>
            </ul>

            <h3>2. PDF Upload</h3>
            <ul>
                <li>A dedicated page allowing users to upload PDF documents for ingestion into the RAG pipeline.</li>
            </ul>

            <h3>3. Local Run Instructions</h3>
            <ul>
                <li>Clear, step-by-step instructions for running the application locally, included in your README.</li>
            </ul>

            <h3>4. Production Deployment Plan</h3>
            <ul>
                <li>A brief written outline of how you would deploy this application to production, covering cloud provider choice, CI/CD strategy, and any infrastructure considerations.</li>
            </ul>

            <div class="bonus">
                <h2>Bonus</h2>
                <ul>
                    <li>Add automated tests for the backend and/or frontend.</li>
                    <li>Document architectural decisions and any notable trade-offs.</li>
                </ul>
            </div>

            <h2>Production Deployment Plan (Example)</h2>
            <p>Provide a short plan describing how you would deploy this application to production. Your write-up should address, at minimum, the following areas:</p>
            <ul>
                <li><strong>Cloud Provider:</strong> Select a cloud platform (e.g., Azure, AWS, or GCP) and justify the choice. Describe how you would host the frontend, backend, and database within that environment.</li>
                <li><strong>CI/CD:</strong> Outline an automated pipeline for testing and deploying changes (e.g., GitHub Actions, Azure DevOps, or similar).</li>
                <li><strong>Data &amp; Secrets Management:</strong> Use managed database services and a secrets manager (e.g., AWS Secrets Manager, Azure Key Vault, or GCP Secret Manager) to avoid hard-coded credentials.</li>
                <li><strong>Observability:</strong> Configure centralised monitoring, structured logging, and alerting so that issues in production are detected promptly.</li>
            </ul>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 36px 0;" />

            <h2>Additional Notes</h2>
            <ul>
                <li>Feel free to expand your README or inline documentation as you progress through the assessment.</li>
                <li>If you make architectural changes from the starter code, document your reasoning clearly.</li>
            </ul>

            <p style="margin-top: 32px; font-weight: 700; font-size: 1.05rem;">Good luck &mdash; we look forward to reviewing your submission!</p>
        </body>
    </html>
    """