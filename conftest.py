import os
import sys

# SOLUTION=1 pytest  -> тестуємо еталонне рішення (solution/iiot), інакше - ваш пакет iiot/
if os.environ.get("SOLUTION") == "1":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "solution"))
