# Utah Watchdog

## Project Overview

This project, "Utah Watchdog," is a web application designed to track Utah's federal and state legislators. It provides information about their votes, campaign financing, and the legislation they are involved in. The application is built with a Python backend and a web-based frontend.

**Key Technologies:**

*   **Backend:** FastAPI (for a potential future REST API)
*   **Frontend:** Streamlit (for the main interactive web interface)
*   **Database:** MongoDB (for storing all data)
*   **Data Ingestion:** Python scripts that fetch data from external sources like the Congress.gov API.
*   **AI Features:** The project is set up to use AI agents, likely for tasks like summarizing legislation or analyzing voting patterns.

**Project Structure:**

*   `src/`: Contains the main source code for the application.
    *   `api/`: FastAPI application.
    *   `agents/`: AI agent-related code.
    *   `config/`: Project configuration.
    *   `database/`: Database connection and schema.
    *   `ingestion/`: Data ingestion scripts and logic.
    *   `models/`: Pydantic models for data structures.
*   `frontend/`: The Streamlit frontend application.
*   `scripts/`: Various scripts for data synchronization, maintenance, and development.
*   `tests/`: Unit and integration tests.

## Building and Running

### 1. Prerequisites

*   Python 3.12+
*   `uv` (for environment and package management)
*   MongoDB instance running

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd utah-watchdog
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    uv venv
    uv sync
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the project root. You can copy the structure from `.env.example` if it exists, or create it from scratch.
    ```
    MONGODB_URI="mongodb://localhost:27017/"
    MONGODB_DATABASE="utah_watchdog"
    CONGRESS_GOV_API_KEY="your-api-key"
    # Add other API keys as needed (OpenAI, FEC, etc.)
    ```

### 3. Running the Application

1.  **Populate the database:**
    Before running the application, you need to sync the data from the external APIs. The most important script to run initially is `sync_members.py`.

    ```bash
    uv run python scripts/pipelines/sync_members.py --state UT
    ```
    You can also run a full sync of all members of congress:
    ```bash
    uv run python scripts/pipelines/sync_all.py
    ```

2.  **Run the Streamlit frontend:**
    ```bash
    uv run streamlit run frontend/app.py
    ```
    The application should now be available at `http://localhost:8501`.

3.  **Run the FastAPI backend (optional):**
    If you want to run the FastAPI backend, use the following command:
    ```bash
    uv run uvicorn src.api.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

## Development Conventions

*   **Code Style:** The project appears to follow standard Python conventions (PEP 8).
*   **Environment Management:** `uv` is used for managing virtual environments and dependencies.
*   **Database Migrations:** There is no formal database migration system in place. Changes to data models may require manual data migration scripts.
*   **Testing:** The `tests/` directory suggests that the project has unit and/or integration tests.
    ```bash
    # TODO: Add instructions on how to run tests.
    ```
