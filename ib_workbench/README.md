# IB Workbench


This is a standalone Django application for running Investment Banking scenarios using the Generative Agents backlog.

![Investment Banking Workbench Simulation Environment](assets/ib_simulation.png)


## Setup

1.  **Prerequisites**: Python 3.9+ is recommended.
2.  **Install Dependencies**:
    ```bash
    pip install Django==2.2 pytz sqlparse
    ```
    *Note: If you want to run the full Reverie simulation, you also need to install the requirements from the root `requirements.txt`.*

## Running the Application

1.  Navigate to this directory:
    ```bash
    cd ib_workbench
    ```
2.  Run migrations (if not already done):
    ```bash
    python3 manage.py migrate
    ```
3.  Start the server:
    ```bash
    python3 manage.py runserver 8001
    ```
4.  Open your browser to: [http://localhost:8001/ib/create/](http://localhost:8001/ib/create/)

## Simulation Modes

-   **Full Simulation**: Requires `reverie` backend dependencies (gensim, scipy, etc.) to be installed.
-   **Mock Simulation**: If dependencies are missing, the application automatically falls back to a mock simulation mode for demonstration purposes.
