"""Run the agent team on one ticket from the command line (from the backend/ folder):

    python run_ticket.py 101

Prints the Boss's outcome and the hand-offs. Every step is also appended to output/audit_trail.json.
Set CAMPUS_DB_PATH to run against a scratch copy of the database instead of the working copy.
"""

import asyncio
import sys

from team import run_ticket


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("usage: python run_ticket.py <ticket_id>")
    result = asyncio.run(run_ticket(int(sys.argv[1])))
    print(result.model_dump_json(indent=2))
    sys.exit(1 if result.error else 0)


if __name__ == "__main__":
    main()
