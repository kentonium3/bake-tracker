#!/usr/bin/env python3
"""
One-time fix script: Delete bare FinishedGoods missing compositions,
then re-create them via the generator script.

The compositions table was not exported/imported in backups prior to
the composition export fix, leaving bare FGs without their component links.

Usage:
    # Close the app first, then:
    python scripts/fix_bare_fg_compositions.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope, init_database, get_engine
from src.models.finished_good import FinishedGood
from src.models import AssemblyType


def main():
    # Initialize database (required for session_scope to work)
    engine = get_engine()
    init_database(engine)

    # Step 1: Delete bare FGs that have no compositions
    with session_scope() as session:
        bare_fgs = (
            session.query(FinishedGood)
            .filter(FinishedGood.assembly_type == AssemblyType.BARE)
            .all()
        )

        orphaned = [fg for fg in bare_fgs if not fg.components]

        if not orphaned:
            print("No orphaned bare FinishedGoods found. Nothing to fix.")
            return

        print(f"Found {len(orphaned)} bare FinishedGoods without compositions.")
        for fg in orphaned:
            print(f"  Deleting: {fg.display_name} (slug={fg.slug})")
            session.delete(fg)

        print(f"\nDeleted {len(orphaned)} orphaned bare FinishedGoods.")

    # Step 2: Re-run the generator
    print("\nRe-creating bare FinishedGoods with compositions...")
    from scripts.generate_bare_finished_goods import generate_bare_finished_goods, print_summary

    results = generate_bare_finished_goods(dry_run=False)
    print_summary(results, dry_run=False)


if __name__ == "__main__":
    main()
