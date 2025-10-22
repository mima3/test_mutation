import logging
import re
import subprocess
import sys
import json
from argparse import Namespace
from collections import defaultdict
from pathlib import Path

from cosmic_ray.config import ConfigDict, load_config
from cosmic_ray.tools.filters.filter_app import FilterApp
from cosmic_ray.work_db import WorkDB
from cosmic_ray.work_item import WorkResult, WorkerOutcome

log = logging.getLogger()


class CoverageFilter(FilterApp):
    """Implements the coverage filter."""

    def description(self):
        return __doc__

    def _check_covered(self, module_path, start_pos_row, end_pos_row, coverage_json):
        files = coverage_json['files'].get(str(module_path), [])
        if not files:
            # カバレッジファイルに記録されていないファイルはカバーしていないとみなす
            return False
        for executed_line in files.get('executed_lines', []):
            # start_pos_row は インポート時に実行されている可能性がある
            if start_pos_row <= executed_line and executed_line <= end_pos_row:
                return True
        return False

    def _skip_filtered(self, work_db, coverage_json):
        skip_job_ids = []
        for item in work_db.pending_work_items:
            for mutation in item.mutations:
                if not mutation.operator_name.startswith("cr_xmt/"):
                    log.info(
                        "no match operator_name skipping %s %s %s %s %s %s",
                        item.job_id,
                        mutation.operator_name,
                        mutation.occurrence,
                        mutation.module_path,
                        mutation.start_pos,
                        mutation.end_pos,
                    )
                    skip_job_ids.append(item.job_id)
                    break
                if not self._check_covered(mutation.module_path, mutation.start_pos[0], mutation.end_pos[0], coverage_json):
                    print(mutation.operator_name, mutation.module_path, mutation.start_pos, mutation.end_pos)
                    log.info(
                        "no covered function skipping %s %s %s %s %s %s",
                        item.job_id,
                        mutation.operator_name,
                        mutation.occurrence,
                        mutation.module_path,
                        mutation.start_pos,
                        mutation.end_pos,
                    )
                    skip_job_ids.append(item.job_id)
                    break

        if skip_job_ids:
            work_db.set_multiple_results(
                skip_job_ids,
                WorkResult(
                    output="Filtered no covered.",
                    worker_outcome=WorkerOutcome.SKIPPED,
                ),
            )

    def filter(self, work_db: WorkDB, args: Namespace):
        """Mark as skipped all work item that is not covered code."""
        if not args.coverage_json:
            raise ValueError("coverage_json is not found.")
        with open(args.coverage_json) as fp:
            coverage_json = json.load(fp)

        self._skip_filtered(work_db, coverage_json)

    def add_args(self, parser):
        parser.add_argument("coverage_json", help="coverage.json path(created by pytest --cov=src --cov-report=json:coverage.json)")


def main(argv=None):
    """Run the operators-filter with the specified command line arguments."""
    return CoverageFilter().main(argv)


if __name__ == "__main__":
    sys.exit(main())
