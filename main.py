# main.py
import os
from dotenv import load_dotenv

load_dotenv()

from app.ui.views.landing import render_landing_page
from app.ui.page_config import apply_page_config

apply_page_config()


def main():
    render_landing_page()


if __name__ == "__main__":
    main()
