# run_streamlit.py
import streamlit.web.cli as stcli
import sys

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "main.py", "--server.port=8501"]
    sys.exit(stcli.main())
