"""Cost reporting"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path
import csv
import json
from .tracker import CostTracker


class CostReporter:
    """Generate cost reports"""
    
    def __init__(self, tracker: CostTracker):
        self.tracker = tracker
    
    def daily_report(
        self,
        date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict:
        """Generate daily cost report"""
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        total_cost = self.tracker.get_total_cost(
            start=start,
            end=end,
            user_id=user_id,
            project_id=project_id,
        )
        
        return {
            "date": start.date().isoformat(),
            "total_cost_usd": total_cost,
            "user_id": user_id,
            "project_id": project_id,
        }
    
    def monthly_report(
        self,
        year: int,
        month: int,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict:
        """Generate monthly cost report"""
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        
        total_cost = self.tracker.get_total_cost(
            start=start,
            end=end,
            user_id=user_id,
            project_id=project_id,
        )
        
        return {
            "year": year,
            "month": month,
            "total_cost_usd": total_cost,
            "user_id": user_id,
            "project_id": project_id,
        }


def generate_cost_report(
    tracker: CostTracker,
    output_path: Path,
    format: str = "json",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> None:
    """Generate and export cost report"""
    reporter = CostReporter(tracker)
    
    if start is None:
        start = datetime.now() - timedelta(days=30)
    if end is None:
        end = datetime.now()
    
    # Get daily breakdown
    daily_costs = []
    current = start
    while current < end:
        daily_report = reporter.daily_report(date=current)
        daily_costs.append(daily_report)
        current += timedelta(days=1)
    
    total_cost = tracker.get_total_cost(start=start, end=end)
    
    report = {
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "total_cost_usd": total_cost,
        "daily_breakdown": daily_costs,
    }
    
    if format == "json":
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
    elif format == "csv":
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "total_cost_usd"])
            writer.writeheader()
            for daily in daily_costs:
                writer.writerow({
                    "date": daily["date"],
                    "total_cost_usd": daily["total_cost_usd"],
                })
    else:
        raise ValueError(f"Unsupported format: {format}")
