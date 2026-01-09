"""Tests for cost tracking"""

import pytest
from datetime import datetime, timedelta
from unified_ai.cost import CostTracker


class TestCostTracker:
    """Test cost tracker"""
    
    def test_record_cost(self, cost_tracker):
        """Test recording costs"""
        cost_tracker.record_cost(
            tool="claude",
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005,
        )
        
        # Verify cost was recorded
        total = cost_tracker.get_total_cost()
        assert total == pytest.approx(0.005, rel=1e-6)
    
    def test_get_total_cost_with_filters(self, cost_tracker):
        """Test getting total cost with filters"""
        # Record costs for different projects
        cost_tracker.record_cost(
            tool="claude",
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005,
            project_id="project1",
        )
        
        cost_tracker.record_cost(
            tool="gpt",
            model="gpt-4",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.10,
            project_id="project2",
        )
        
        # Total cost
        total = cost_tracker.get_total_cost()
        assert total == pytest.approx(0.105, rel=1e-6)
        
        # Cost for project1 only
        project1_cost = cost_tracker.get_total_cost(project_id="project1")
        assert project1_cost == pytest.approx(0.005, rel=1e-6)
    
    def test_get_total_cost_time_range(self, cost_tracker):
        """Test getting total cost for time range"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # Record cost
        cost_tracker.record_cost(
            tool="claude",
            model="claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005,
        )
        
        # Should be included in current period
        total = cost_tracker.get_total_cost(start=yesterday, end=tomorrow)
        assert total == pytest.approx(0.005, rel=1e-6)
        
        # Should not be included in future period
        future_total = cost_tracker.get_total_cost(start=tomorrow)
        assert future_total == 0.0
