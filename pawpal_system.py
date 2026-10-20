"""PawPal+ logic layer: backend classes for pet care planning (skeleton only)."""

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    preferred_time: Optional[time] = None
    frequency: str = "daily"  # "once" | "daily" | "weekly"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        pass

    def is_due(self, on_date: date) -> bool:
        """Return True if this task should happen on the given date."""
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int = 0
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        pass


@dataclass
class Owner:
    name: str
    available_minutes: int = 120
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_all_tasks(self) -> list[Task]:
        """Collect tasks across all of the owner's pets."""
        pass


@dataclass
class ScheduledItem:
    task: Task
    start_time: time
    end_time: time
    reason: str = ""


class Scheduler:
    def __init__(self, owner: Owner, day_start: time = time(8, 0)):
        self.owner = owner
        self.day_start = day_start

    def generate_plan(self, on_date: date) -> tuple[list[ScheduledItem], list[Task]]:
        """Build a daily plan; return (scheduled items, skipped tasks)."""
        pass

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority, then duration."""
        pass

    def _due_tasks(self, on_date: date) -> list[Task]:
        """Return incomplete tasks due on the given date."""
        pass
