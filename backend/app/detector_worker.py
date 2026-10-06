"""Run with python -m app.detector_worker [--once] from backend."""
import argparse
import logging
import os
from pathlib import Path
import signal
from threading import Event

from dotenv import load_dotenv
import psycopg

from app.detector import Config, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true', help='Evaluate once and exit; respects the persisted cadence.')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    config = Config.from_env()
    if not os.getenv('DATABASE_URL'):
        parser.error('DATABASE_URL is required. Apply Alembic migrations before starting the worker.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    stop = Event()
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: stop.set())
    logging.info('Request-failure detector started; window=%ss interval=%ss', config.window_seconds,config.interval_seconds)
    while not stop.is_set():
        try:
            with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True,connect_timeout=3) as connection:
                logging.info('Detector evaluation: %s', evaluate(connection,config))
        except psycopg.Error:
            # Do not log connection strings, row contents, or database error details.
            logging.error('Detector database operation failed; transaction rolled back. Check database/migrations.')
            if args.once:
                return 1
        if args.once:
            return 0
        stop.wait(config.interval_seconds)
    logging.info('Detector stopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
