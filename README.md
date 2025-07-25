# AI-Powered Jira Ticket Automation API

## Overview

This project is a sophisticated, AI-powered automation service designed to bridge the gap between development activities and project management. It intelligently converts developer code commits and client feature requests directly into structured, actionable Jira tickets.

The application uses Google's Gemini 2.5 Pro model to classify incoming text and generate context-aware Jira issues, including Epics, Stories, Tasks, Bugs, and Sub-tasks. It maintains a complete audit trail of all activities in a MySQL database and uses a ChromaDB vector store for contextual understanding. The entire service is built with FastAPI and is designed to be deployed as a containerized application.

## Features

- **Dual-Input Automation:** Handles both developer-centric inputs (Git commits) and client-centric inputs (natural language feature requests).
- **Intelligent Classification:** Utilizes a "gatekeeper" AI step to classify inputs as substantive, non-substantive, or vague, preventing the creation of unnecessary tickets.
- **Context-Aware Generation:** Leverages a ChromaDB vector database to find related existing issues, providing the AI with context to correctly link new tickets (e.g., linking a new Story to the correct Epic).
- **Automatic Jira Creation:** Seamlessly creates and assigns issues in Jira using the REST API, correctly handling different issue types and parent-child relationships.
- **Comprehensive Auditing:** Logs every step of the process—from the initial request to the final ticket creation—in a robust MySQL database for full traceability.
- **Containerized Deployment:** Includes a `Dockerfile` for easy and consistent deployment in any containerized environment, such as AWS ECS or Google Cloud Run.

## Technology Stack

- **Backend Framework:** FastAPI
- **AI Model:** Google Gemini 2.5 Pro (via Vertex AI)
- **Database:** MySQL
- **ORM:** SQLAlchemy
- **Vector Database:** ChromaDB
- **Deployment:** Docker, Uvicorn

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

- Python 3.12 or later
- A running MySQL database
- Git

### 2. Clone the Repository

git clone <your-repository-url>
cd <your-repository-directory>

3. Set up a Virtual Environment
It is highly recommended to use a virtual environment.

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

4. Install Dependencies
Install all the required Python packages using the requirements.txt file.

pip install -r requirements.txt

5. Configure Environment Variables
The application uses a .env file to manage secrets and configuration. Create a file named .env in the root of the project and add the following content, replacing the placeholder values with your actual credentials.

# Jira Credentials
JIRA_EMAIL="your_jira_email@example.com"
JIRA_API_TOKEN="your_jira_api_token_here"

# Database Credentials
DB_USER="your_database_user"
DB_PASSWORD="your_database_password"
DB_HOST="localhost" # Or the IP/hostname of your database server
DB_NAME="your_database_name"

# Running the Application
Locally with Uvicorn
Once your .env file is configured, you can run the application directly with Uvicorn.

uvicorn main:app --host 0.0.0.0 --port 8080 --reload

The application will be available at http://localhost:8080.

# Using Docker
The project includes a Dockerfile for containerized deployment.

Build the Docker image:

docker build -t jira-automation-api .

# Run the Docker container:
Make sure to pass your .env file to the container.

docker run -d --env-file .env -p 8080:8080 jira-automation-api

# API Endpoints
Jira Data Fetcher
GET /simplified-jira-issues: A utility endpoint to fetch and simplify issue data from a given Jira JQL query. Requires Jira credentials as query parameters.

# Automation Logs Database
GET /requests: Retrieves a paginated list of all initial automation requests that have been logged.

GET /classifications: Retrieves a paginated list of all AI classification decisions.

GET /tickets: Retrieves a paginated list of all successfully created Jira tickets.

GET /full_log/{request_id}: Retrieves the complete audit trail for a single request, from input to final ticket.

Jira Ticket Generation
POST /generate_ticket: The primary endpoint for developers. It accepts a commit message and automatically creates a corresponding Task, Bug, or Sub-task in Jira.

Request Body:

{
  "commit_message": "feat: Added Google OAuth to login page",
  "repo": "my-org/my-project",
  "assignee_email": "developer@example.com"
}

POST /generate_client_ticket: The primary endpoint for clients. It accepts a natural language request and automatically creates a corresponding Epic or Story in Jira.

Request Body:

{
  "request_text": "I want a dashboard to see my monthly sales",
  "repo": "my-org/my-project",
  "assignee_email": "product.manager@example.com"
}
