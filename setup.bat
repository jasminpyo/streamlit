@echo off
echo Setting up Streamlit RAG Chatbot Environment...
echo.

echo Creating virtual environment...
python -m venv venv
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

echo Installing required packages...
pip install -r requirements.txt
echo.

echo Setup complete!
echo.
echo To run the application:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Configure your .env file with AWS credentials
echo 3. Run: streamlit run main.py
echo.
pause