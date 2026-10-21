"""PawPal+ logic layer: backend classes for pet care planning."""

from bisect import insort
from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from enum import IntEnum
from itertools import combinations
from typing import Optional
from uuid import uuid4

FREQUENCIES = ("once", "daily", "weekly")
RECURRENCE_DAYS = {"daily": 1, "weekly": 7}
MINUTES_PER_DAY = 24 * 60
LAST_MINUTE = MINUTES_PER_DAY - 1  # plans must end by 23:59


class Priority(IntEnum):
    """Higher value = more important, so tasks sort correctly with reverse=True."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


# Knapsack value of each priority: one HIGH task outweighs three MEDIUM tasks.
PRIORITY_VALUE = {Priority.LOW: 1, Priority.MEDIUM: 3, Priority.HIGH: 9}
# Scales value so it always outweighs the duration tie-break (total minutes <= 1440).
VALUE_SCALE = 10_000


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
    start_date: date = field(default_factory=date.today)  # first date this occurrence is due
    last_completed: Optional[date] = None
    earliest: Optional[time] = None  # may not start before this time
    latest: Optional[time] = None  # must be finished by this time
    after: Optional[str] = None  # id of a task that must finish before this one starts
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        """Reject non-positive durations, unknown frequencies and bad windows."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}")
        if self.earliest and self.latest and self.earliest >= self.latest:
            raise ValueError("earliest must be before latest")
        if self.after == self.id:
            raise ValueError("a task cannot come after itself")

    def mark_complete(self, on_date: date) -> None:
        """Record that this task was completed on the given date."""
        self.last_completed = on_date

    def is_due(self, on_date: date) -> bool:
        """Return True if the task has started and has not been completed.

        Recurrence is handled by Pet.complete_task, which creates the next
        occurrence as a new Task, so each Task is a single occurrence.
        """
        return self.last_completed is None and on_date >= self.start_date

    def is_overdue(self, on_date: date) -> bool:
        """Return True if the task was due before `on_date` and is still open.

        Overdue tasks get a one-level priority boost when a plan is built.
        """
        return self.is_due(on_date) and self.start_date < on_date


@dataclass
class Pet:
    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def complete_task(self, task: Task, on_date: date) -> Optional[Task]:
        """Mark `task` done and, if it repeats, queue its next occurrence.

        Args:
            task: A task belonging to this pet.
            on_date: The day it was completed. A daily task's next occurrence
                starts the following day, a weekly task's seven days later.

        Returns:
            The newly added Task (same details, fresh id, not completed), or
            None for a "once" task, which does not repeat.
        """
        task.mark_complete(on_date)
        days = RECURRENCE_DAYS.get(task.frequency)
        if days is None:  # "once": nothing to repeat
            return None
        next_task = replace(
            task,
            start_date=on_date + timedelta(days=days),
            last_completed=None,
            id=uuid4().hex,  # a new occurrence needs its own identity
        )
        self.add_task(next_task)
        return next_task


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
    def __init__(
        self,
        owner: Owner,
        day_start: time = time(8, 0),
        day_end: time = time(23, 59),
        buffer_minutes: int = 0,
        max_drift_minutes: Optional[int] = None,
    ):
        """Create a scheduler for an owner.

        day_start/day_end bound the day for tasks without a preferred time,
        buffer_minutes is the gap kept between tasks, and max_drift_minutes
        (None = unlimited) caps how far a task may move from its preferred time.
        """
        self.owner = owner
        self.day_start = day_start
        self.day_end = day_end
        self.buffer_minutes = buffer_minutes
        self.max_drift_minutes = max_drift_minutes

    def generate_plan(
        self, on_date: date
    ) -> tuple[list[ScheduledItem], list[tuple[Task, str]]]:
        """Build the plan for one day.

        Steps: choose which due tasks fit the time budget (`_select_tasks`),
        group each pet's tasks and order them by preferred time, then place
        each in the free slot nearest its preferred time (`_place`), honoring
        dependencies, time windows, buffers and the day's bounds.

        Args:
            on_date: The day to plan for. Only tasks due on it are considered.

        Returns:
            (items, skipped): the scheduled items sorted by start time, and
            (task, reason) pairs for every due task that was left out.
        """
        # 1. Choose which due tasks fit the time budget (0/1 knapsack on priority).
        # 2. Order them: same-pet tasks together, then by preferred time.
        # 3. Place each in the free slot nearest its preferred time, after its
        #    dependency, inside its time window and the day's bounds.
        due = self._due_tasks(on_date)
        titles = {t.id: t.title for _, t in due}
        chosen, skipped = self._select_tasks(due, on_date)

        pet_order = {id(p): i for i, p in enumerate(self.owner.pets)}
        chosen.sort(key=lambda pt: pet_order[id(pt[0])])  # group a pet's tasks
        pet_for = {task.id: pet for pet, task in chosen}
        pending = self.sort_by_time([t for _, t in chosen])
        due_ids = set(titles)
        chosen_ids = {t.id for t in pending}

        busy: list[tuple[int, int]] = []  # occupied [start, end), kept sorted
        placed: dict[str, int] = {}  # task id -> end minute
        failed: set[str] = set()
        items: list[ScheduledItem] = []

        while pending:
            task = next((t for t in pending if self._ready(t, chosen_ids, placed, failed)),
                        None)
            if task is None:  # every remaining task waits on another: a cycle
                skipped += [(t, "circular dependency between tasks") for t in pending]
                break
            pending.remove(task)
            pet = pet_for[task.id]

            min_start = 0
            if task.after in due_ids:
                if task.after not in chosen_ids or task.after in failed:
                    skipped.append((task, f"depends on '{titles[task.after]}', "
                                          f"which isn't in today's plan"))
                    failed.add(task.id)
                    continue
                min_start = placed[task.after]

            slot, wanted, why_not = self._place(task, busy, min_start)
            if slot is None:
                skipped.append((task, why_not))
                failed.add(task.id)
                continue
            end = slot + task.duration_minutes
            insort(busy, (slot, end))
            placed[task.id] = end
            items.append(ScheduledItem(
                task=task, pet_name=pet.name,
                start_time=_to_time(slot), end_time=_to_time(end),
                reason=self._reason(task, slot, wanted, on_date,
                                    titles.get(task.after) if task.after in due_ids else None),
            ))

        items.sort(key=lambda i: i.start_time)
        return items, skipped

    @staticmethod
    def _ready(task: Task, chosen_ids: set, placed: dict, failed: set) -> bool:
        """Return True once the task can be placed.

        That is the case when it has no dependency, the dependency is not part
        of today's plan, or the dependency has already been placed or has
        failed to place (so the dependent task can be skipped with a reason).
        """
        return (task.after not in chosen_ids
                or task.after in placed or task.after in failed)

    def _effective_priority(self, task: Task, on_date: date) -> Priority:
        """Return the priority used for planning.

        An overdue task is raised one level (capped at HIGH) so work that was
        already missed is not pushed out again by fresh tasks.
        """
        if task.is_overdue(on_date):
            return Priority(min(Priority.HIGH, task.priority + 1))
        return task.priority

    def _select_tasks(
        self, due: list[tuple[Pet, Task]], on_date: date
    ) -> tuple[list[tuple[Pet, Task]], list[tuple[Task, str]]]:
        """Pick the due tasks worth the most within the time budget (0/1 knapsack).

        Each task is an item whose weight is its duration and whose value comes
        from its effective priority (HIGH 9, MEDIUM 3, LOW 1). Dynamic
        programming over whole minutes finds the best-valued set that fits the
        owner's budget (capped at one day). Value dominates; among equally
        valuable sets the one using fewer minutes wins.

        Args:
            due: (pet, task) pairs due on `on_date`.
            on_date: The day being planned (used for the overdue boost).

        Returns:
            (chosen, skipped): the selected pairs, and (task, reason) pairs for
            the rest, ordered by priority then duration.
        """
        budget = min(self.owner.available_minutes, MINUTES_PER_DAY)
        fits = [(p, t) for p, t in due if t.duration_minutes <= budget]
        score = [PRIORITY_VALUE[self._effective_priority(t, on_date)] * VALUE_SCALE
                 - t.duration_minutes for _, t in fits]

        best = [0] * (budget + 1)  # best[w] = top score using at most w minutes
        took = [[False] * (budget + 1) for _ in fits]
        for i, (_, task) in enumerate(fits):
            d = task.duration_minutes
            for w in range(budget, d - 1, -1):
                if best[w - d] + score[i] > best[w]:
                    best[w] = best[w - d] + score[i]
                    took[i][w] = True

        picked: set[int] = set()
        w = budget
        for i in range(len(fits) - 1, -1, -1):
            if took[i][w]:
                picked.add(i)
                w -= fits[i][1].duration_minutes

        chosen = [pt for i, pt in enumerate(fits) if i in picked]
        chosen_ids = {t.id for _, t in chosen}
        skipped = []
        for _, task in sorted(due, key=lambda pt: (-self._effective_priority(pt[1], on_date),
                                                    pt[1].duration_minutes)):
            if task.id in chosen_ids:
                continue
            if task.duration_minutes > budget:
                reason = (f"needs {task.duration_minutes} min but the whole daily "
                          f"budget is {budget} min")
            else:
                reason = (f"left out so the {budget}-min daily budget goes to "
                          f"higher-value tasks")
            skipped.append((task, reason))
        return chosen, skipped

    def _place(
        self, task: Task, busy: list[tuple[int, int]], min_start: int
    ) -> tuple[Optional[int], int, str]:
        """Find where a task should start, given the slots already taken.

        Builds the allowed range from the day's bounds, the task's own
        earliest/latest window and `min_start` (the end of its dependency),
        then asks `_find_slot` for the free slot nearest the preferred time.
        A task with no preferred time wants the start of the day.

        Args:
            task: The task to place.
            busy: Occupied (start, end) minutes, sorted by start.
            min_start: Earliest allowed start, in minutes since midnight.

        Returns:
            (start, wanted, reason): the start minute (None if it cannot be
            placed), the minute the task asked for, and a skip reason (empty
            on success). A slot farther than `max_drift_minutes` from the
            preferred time counts as not placeable.
        """
        day_start = _to_minutes(self.day_start)
        if task.preferred_time:
            wanted = _to_minutes(task.preferred_time)
            lo = min(day_start, wanted)
        else:
            wanted = lo = day_start
        if task.earliest:
            lo = max(lo, _to_minutes(task.earliest))
            wanted = max(wanted, lo)
        lo = max(lo, min_start)
        hi = min(_to_minutes(self.day_end), LAST_MINUTE)
        if task.latest:
            hi = min(hi, _to_minutes(task.latest))

        start = self._find_slot(busy, wanted, task.duration_minutes, lo, hi,
                                self.buffer_minutes)
        if start is None:
            return None, wanted, (f"no free {task.duration_minutes}-min slot between "
                                  f"{_to_time(min(lo, LAST_MINUTE)):%H:%M} and "
                                  f"{_to_time(max(hi, 0)):%H:%M}")
        drift = abs(start - wanted)
        if (task.preferred_time and self.max_drift_minutes is not None
                and drift > self.max_drift_minutes):
            return None, wanted, (f"nearest free slot ({_to_time(start):%H:%M}) is "
                                  f"{drift} min from its preferred time, over the "
                                  f"{self.max_drift_minutes}-min limit")
        return start, wanted, ""

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching a pet name and/or completion status.

        Either filter may be omitted (None) to match everything. Each Task is a
        single occurrence, so it is completed once it has a last_completed date.

        Args:
            pet_name: Case-insensitive pet name, or None for all pets.
            completed: True for finished tasks, False for open ones, None for both.

        Returns:
            (pet, task) pairs in the owner's pet and task order.
        """
        matches = []
        for pet, task in self.owner.get_all_tasks():
            if pet_name is not None and pet.name.lower() != pet_name.lower():
                continue
            if completed is not None and (task.last_completed is not None) != completed:
                continue
            matches.append((pet, task))
        return matches

    def find_conflicts(self, on_date: date) -> list[str]:
        """Return warning messages for due tasks whose preferred times overlap.

        Lightweight check: only tasks with a preferred_time are compared, for
        the same pet or different pets. It never raises; no conflicts -> [].
        generate_plan still shifts the later task, so these warnings explain
        why a task did not get its preferred time.

        Tasks are sorted by start time and every earlier/later pair is checked:
        the pair clashes when the later task starts before the earlier ends.
        Back-to-back tasks do not clash.

        Args:
            on_date: The day to check; only tasks due on it are compared.

        Returns:
            One message per clashing pair, naming both tasks, their times and
            whether they are for the same pet.
        """
        timed = sorted(
            ((_to_minutes(t.preferred_time), pet, t)
             for pet, t in self._due_tasks(on_date) if t.preferred_time),
            key=lambda x: x[0],
        )
        # Every pair (earlier, later): they clash if the later one starts
        # before the earlier one ends.
        return [
            f"Conflict ({'same pet' if pet_a is pet_b else 'different pets'}): "
            f"{self._describe(pet_a, task_a, start_a)} overlaps "
            f"{self._describe(pet_b, task_b, start_b)}"
            for (start_a, pet_a, task_a), (start_b, pet_b, task_b)
            in combinations(timed, 2)
            if start_b < start_a + task_a.duration_minutes
        ]

    @staticmethod
    def _describe(pet: Pet, task: Task, start: int) -> str:
        """Format "Pet's 'Task' (HH:MM-HH:MM)" for a task starting at `start` minutes."""
        end = start + task.duration_minutes
        return f"{pet.name}'s '{task.title}' ({_to_time(start):%H:%M}-{_to_time(end):%H:%M})"

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by preferred time, earliest first.

        Tasks with no preferred time go last. The sort is stable, so tasks with
        equal times keep their original order. The key compares zero-padded
        "HH:MM" strings, which sort chronologically as plain text.
        """
        # Zero-padded "HH:MM" strings sort chronologically as plain text.
        return sorted(
            tasks,
            key=lambda t: (t.preferred_time is None,
                           f"{t.preferred_time:%H:%M}" if t.preferred_time else ""),
        )

    def _due_tasks(self, on_date: date) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs due on the given date, across all pets."""
        return [(p, t) for p, t in self.owner.get_all_tasks() if t.is_due(on_date)]

    @staticmethod
    def _find_slot(
        busy: list[tuple[int, int]], wanted: int, length: int,
        lo: int, hi: int, buffer: int = 0,
    ) -> Optional[int]:
        """Start of the free slot nearest `wanted` (before or after), or None.

        `busy` is sorted by start. Free gaps inside [lo, hi] are scanned once;
        each gap is padded by `buffer` minutes around occupied slots. Ties go to
        the earlier slot.

        Args:
            busy: Occupied (start, end) minutes, sorted by start.
            wanted: The start minute the task would like.
            length: The task's duration in minutes.
            lo, hi: The task must start at or after `lo` and finish by `hi`.
            buffer: Minimum gap to keep between this and other tasks.

        Returns:
            The best start minute, or None if no gap is long enough.
        """
        best: Optional[tuple[int, int]] = None  # (distance, start)

        def consider(gap_start: int, gap_end: int) -> None:
            nonlocal best
            if gap_end - gap_start >= length:
                start = min(max(wanted, gap_start), gap_end - length)
                cand = (abs(start - wanted), start)
                if best is None or cand < best:
                    best = cand

        cursor = lo
        for b_start, b_end in busy:
            if b_start - buffer > cursor:
                consider(cursor, min(b_start - buffer, hi))
            cursor = max(cursor, b_end + buffer)
        consider(cursor, hi)
        return best[1] if best else None

    @staticmethod
    def _reason(
        task: Task, start: int, wanted: int, on_date: date,
        after_title: Optional[str] = None,
    ) -> str:
        """Explain in one sentence why the task was placed at `start`.

        Mentions the (possibly boosted) priority, any dependency it follows,
        and whether it got its preferred time, was moved, or took the earliest
        free slot.
        """
        text = f"{task.priority.name.lower()} priority"
        if task.is_overdue(on_date) and task.priority < Priority.HIGH:
            text += " (raised a level: overdue)"
        elif task.is_overdue(on_date):
            text += " (overdue)"
        if after_title:
            text += f"; follows '{after_title}'"
        if task.preferred_time is None:
            return f"{text}; placed in the earliest free slot"
        if start == wanted:
            return f"{text}; scheduled at its preferred time"
        return (f"{text}; preferred time {task.preferred_time:%H:%M} was taken, "
                f"moved to {_to_time(start):%H:%M}")
