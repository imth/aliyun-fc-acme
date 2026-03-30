import logging

from src.main import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def handler(event, context):
    return run()
