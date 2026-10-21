"""PawPal+ logic layer: backend classes for pet care planning."""

from dataclasses import dataclass, field
from datetime import date, time
from enum import IntEnum
from typing import Optional
from uuid import uuid4

FREQUENCIES = ("once", "daily", "weekly")
MINUTES_PER_DAY = 24 * 60


class Priority(IntEnum):
    """Higher value = more important, so tasks sort correctly with reverse=True."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _to_minutes(t: time) -> int:
    """Convert a time of day to minutes since midnight."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes since midnight to a time of day."""
    return time(minutes // 60, minutes % 60)


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    preferred_time: Optional[time] = None
    frequency: str = "daily"  # "once" | "daily" | "weekly"
    start_date: date = field(default_factory=date.today)  # anchor for once/weekly
    last_completed: Optional[date] = None
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        """Reject non-positive durations and unknown frequencies."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}")

    def mark_complete(self, on_date: date) -> None:
        """Record that this task was completed on the given date."""
        self.last_completed = on_date

    def is_due(self, on_date: date) -> bool:
        """Return True if the task is due on the given date and not yet completed."""
        if on_date < self.start_date:
            return False
        if self.frequency == "once":
            return self.last_completed is None
        if self.last_completed == on_date:
            return False
        if self.frequency == "weekly":
            return (on_date - self.start_date).days % 7 == 0
        return True  # daily


@dataclass
class Pet:
    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)


@dataclass
class Owner:
    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Collect (pet, task) pairs across all of the owner's pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class ScheduledItem:
    task: Task
    pet_name: str
    start_time: time
    end_time: time
    reason: str = ""


class Scheduler:
    def __init__(self, owner: Owner, day_start: time = time(8, 0)):
        """Create a scheduler for an owner, with the day starting at day_start."""
        self.owner = owner
        self.day_start = day_start

    def generate_plan(
        self, on_date: date
    ) -> tuple[list[ScheduledItem], list[tuple[Task, str]]]:
        """Build a daily plan; return (scheduled items, [(skipped task, reason)])."""
        # Pick tasks by priority until the time budget is used up (a task that
        # doesn't fit is skipped, and smaller ones are still tried). Tasks with a
        # preferred time are then placed first, shifted past any overlap; the
        # rest fill the earliest free gaps from day_start.
        ranked = self._sort_tasks(self._due_tasks(on_date))

        chosen: list[tuple[Pet, Task]] = []
        skipped: list[tuple[Task, str]] = []
        remaining = self.owner.available_minutes
        for pet, task in ranked:
            if task.duration_minutes <= remaining:
                chosen.append((pet, task))
                remaining -= task.duration_minutes
            else:
                skipped.append(
                    (task, f"needs {task.duration_minutes} min but only "
                           f"{remaining} min of the daily budget remain")
                )

        busy: list[tuple[int, int]] = []  # occupied [start, end) in minutes
        items: list[ScheduledItem] = []
        timed = [c for c in chosen if c[1].preferred_time is not None]
        untimed = [c for c in chosen if c[1].preferred_time is None]
        for pet, task in timed + untimed:
            wanted = (_to_minutes(task.preferred_time) if task.preferred_time
                      else _to_minutes(self.day_start))
            start = self._first_free(busy, wanted, task.duration_minutes)
            end = start + task.duration_minutes
            if end >= MINUTES_PER_DAY:
                skipped.append((task, "no free slot left before midnight"))
                continue
            busy.append((start, end))
            items.append(ScheduledItem(
                task=task, pet_name=pet.name,
                start_time=_to_time(start), end_time=_to_time(end),
                reason=self._reason(task, start, wanted),
            ))

        items.sort(key=lambda i: i.start_time)
        return items, skipped

    def _sort_tasks(
        self, pairs: list[tuple[Pet, Task]]
    ) -> list[tuple[Pet, Task]]:
        """Order (pet, task) pairs by priority (high first), then shortest first."""
        return sorted(
            pairs, key=lambda pt: (-pt[1].priority, pt[1].duration_minutes)
        )

    def _due_tasks(self, on_date: date) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs due on the given date, across all pets."""
        return [(p, t) for p, t in self.owner.get_all_tasks() if t.is_due(on_date)]

    @staticmethod
    def _first_free(busy: list[tuple[int, int]], start: int, length: int) -> int:
        """Earliest start >= `start` where `length` minutes don't overlap `busy`."""
        moved = True
        while moved:
            moved = False
            for b_start, b_end in busy:
                if start < b_end and b_start < start + length:
                    start = b_end
                    moved = True
        return start

    @staticmethod
    def _reason(task: Task, start: int, wanted: int) -> str:
        """Explain in one sentence why the task was placed at `start`."""
        text = f"{task.priority.name.lower()} priority"
        if task.preferred_time is None:
            return f"{text}; placed in the earliest free slot"
        if start == wanted:
            return f"{text}; scheduled at its preferred time"
        return (f"{text}; preferred time {task.preferred_time:%H:%M} was taken, "
                f"moved to {_to_time(start):%H:%M}")
