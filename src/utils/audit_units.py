"""
Unit audit script for identifying non-standard unit values in the database.

TD-002 Technical Debt: Unit Standardization
This script audits all unit columns across the database and reports any values
that are not in the standard ALL_UNITS list.

Usage:
    python -m src.utils.audit_units              # Print report to stdout
    python -m src.utils.audit_units --output FILE  # Save report to file

Note: This script uses raw SQL to handle schema differences between the model
definitions and actual database state (e.g., purchase_unit vs package_unit).
"""

import argparse
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from sqlalchemy import text, inspect

from src.services.database import get_engine, init_database
from src.utils.constants import (
    ALL_UNITS,
    MEASUREMENT_UNITS,
    WEIGHT_UNITS,
    VOLUME_UNITS,
    COUNT_UNITS,
    PACKAGE_UNITS,
)


# Audit configuration: (table_name, column_name, valid_units, alternate_column)
# valid_units=None means use ALL_UNITS
# alternate_column is checked if primary column doesn't exist (for schema migrations)
AUDIT_CONFIG: List[Tuple[str, str, Optional[List[str]], Optional[str]]] = [
    ("products", "package_unit", MEASUREMENT_UNITS, "purchase_unit"),  # Measurement units only
    ("ingredients", "density_volume_unit", VOLUME_UNITS, None),
    ("ingredients", "density_weight_unit", WEIGHT_UNITS, None),
    ("recipe_ingredients", "unit", MEASUREMENT_UNITS, None),  # Measurement units only
    ("recipes", "yield_unit", None, None),  # ALL_UNITS - yield_unit is more flexible
    ("finished_units", "item_unit", None, None),  # ALL_UNITS - item_unit is descriptive
    ("production_consumptions", "unit", MEASUREMENT_UNITS, None),  # Measurement units only
    ("assembly_packaging_consumptions", "unit", ALL_UNITS, None),
]


class AuditFinding:
    """Represents a single non-standard unit finding."""

    def __init__(self, table: str, column: str, record_id: int, value: str, valid_units: List[str]):
        self.table = table
        self.column = column
        self.record_id = record_id
        self.value = value
        self.valid_units = valid_units

    def __repr__(self) -> str:
        return f'  ID {self.record_id}: {self.column} = "{self.value}" (not in valid units)'


def get_table_columns(engine, table_name: str) -> List[str]:
    """Get list of column names for a table."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return [col["name"] for col in columns]


def audit_unit_column(
    engine,
    table_name: str,
    column_name: str,
    valid_units: List[str],
    alternate_column: Optional[str] = None,
) -> List[AuditFinding]:
    """
    Audit a single unit column for non-standard values using raw SQL.

    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table to audit
        column_name: Name of the unit column to audit
        valid_units: List of valid unit values to check against
        alternate_column: Fallback column name if primary doesn't exist

    Returns:
        List of AuditFinding objects for non-standard values
    """
    findings = []

    # Check if table exists
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return findings

    # Check which column name to use
    table_columns = get_table_columns(engine, table_name)
    actual_column = column_name

    if column_name not in table_columns:
        if alternate_column and alternate_column in table_columns:
            actual_column = alternate_column
        else:
            # Column doesn't exist, skip
            return findings

    valid_lower = [u.lower() for u in valid_units]

    # Query using raw SQL
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT id, {actual_column} FROM {table_name}"))
        rows = result.fetchall()

    for row in rows:
        record_id = row[0]
        value = row[1]

        # Skip None/NULL values (they're allowed for optional fields)
        if value is None:
            continue

        # Check if value is valid (case-insensitive)
        if value.lower() not in valid_lower:
            finding = AuditFinding(
                table=table_name,
                column=actual_column,
                record_id=record_id,
                value=value,
                valid_units=valid_units,
            )
            findings.append(finding)

    return findings


def run_full_audit(engine) -> Dict[str, List[AuditFinding]]:
    """
    Run audit on all configured unit columns.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Dictionary mapping table names to lists of findings
    """
    results: Dict[str, List[AuditFinding]] = {}

    for table_name, column_name, valid_units, alternate_column in AUDIT_CONFIG:
        # Use ALL_UNITS if no specific list provided
        units_to_check = valid_units if valid_units is not None else ALL_UNITS

        findings = audit_unit_column(
            engine, table_name, column_name, units_to_check, alternate_column
        )

        if findings:
            if table_name not in results:
                results[table_name] = []
            results[table_name].extend(findings)

    return results


def generate_report(results: Dict[str, List[AuditFinding]]) -> str:
    """
    Generate a formatted audit report.

    Args:
        results: Dictionary of audit findings by table

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("Unit Audit Report")
    lines.append("=================")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    total_findings = sum(len(findings) for findings in results.values())

    if total_findings == 0:
        lines.append("Non-standard units found: 0")
        lines.append("")
        lines.append("All unit values in the database are valid.")
    else:
        lines.append(f"Non-standard units found: {total_findings}")
        lines.append("")

        # Group findings by table
        for table_name, findings in sorted(results.items()):
            lines.append(f"Table: {table_name}")

            for finding in findings:
                lines.append(str(finding))

            lines.append("")

    # Add reference section
    lines.append("Standard Units Reference")
    lines.append("------------------------")
    lines.append(f"Weight:  {', '.join(WEIGHT_UNITS)}")
    lines.append(f"Volume:  {', '.join(VOLUME_UNITS)}")
    lines.append(f"Count:   {', '.join(COUNT_UNITS)}")
    lines.append(f"Package: {', '.join(PACKAGE_UNITS)}")
    lines.append("")
    lines.append(f"Total valid units: {len(ALL_UNITS)}")

    return "\n".join(lines)


def run_audit(output_file: Optional[str] = None) -> Tuple[int, str]:
    """
    Run the full unit audit and generate report.

    Args:
        output_file: Optional file path to save report to

    Returns:
        Tuple of (total_findings, report_string)
    """
    # Get database engine
    engine = get_engine()

    # Run audit
    results = run_full_audit(engine)
    report = generate_report(results)
    total_findings = sum(len(findings) for findings in results.values())

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: {output_file}")

    return total_findings, report


def main():
    """CLI entry point for the audit script."""
    parser = argparse.ArgumentParser(description="Audit database for non-standard unit values")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for the report (default: print to stdout)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only output the count of non-standard units"
    )

    args = parser.parse_args()

    try:
        total_findings, report = run_audit(args.output)

        if args.quiet:
            print(total_findings)
        elif not args.output:
            print(report)

        # Exit with non-zero status if findings exist
        sys.exit(0 if total_findings == 0 else 1)

    except Exception as e:
        print(f"Error running audit: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
