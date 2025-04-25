# Tradeverse Trading Journal

A full-stack web application for traders to log, track, and analyze their trades. Built with FastAPI and Streamlit.

## Features

- User authentication (register/login)
- Trade input form with all essential fields
- Performance dashboard with key metrics
- Interactive charts and visualizations
- Trade log with filtering capabilities
- Personalized improvement recommendations
- Mobile-responsive design

## Tech Stack

- Backend: FastAPI
- Frontend: Streamlit
- Database: SQLite (can be configured to use PostgreSQL)
- Authentication: JWT
- Visualization: Plotly

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd tradeverse
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./tradeverse.db
API_URL=http://localhost:8000
```

5. Start the FastAPI backend:
```bash
uvicorn main:app --reload
```

6. In a new terminal, start the Streamlit frontend:
```bash
streamlit run app.py
```

7. Open your browser and navigate to:
- Frontend: http://localhost:8501
- Backend API docs: http://localhost:8000/docs

## Usage

1. Register a new account or login with existing credentials
2. Use the trade input form to log your trades
3. View your performance metrics and charts in the dashboard
4. Check the trade log to see all your trades
5. Get personalized recommendations for improvement

## API Endpoints

- POST /register - Register a new user
- POST /token - Login and get access token
- POST /trades - Create a new trade
- GET /trades - Get all trades for the authenticated user

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 