"""Temporary CLI testing ground for the PawPal+ logic layer."""

from datetime import date, time, timedelta

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def build_owner(minutes: int) -> tuple[Owner, Pet, Pet]:
    owner = Owner("Jordan", available_minutes=minutes)
    biscuit = Pet("Biscuit", "dog", age=4)
    mochi = Pet("Mochi", "cat", age=2)
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return owner, biscuit, mochi


def show(title: str, scheduler: Scheduler, today: date) -> None:
    print(f"\n{title}")
    print("=" * 60)
    for warning in scheduler.find_conflicts(today):
        print(f"WARNING: {warning}")
    items, skipped = scheduler.generate_plan(today)
    for item in items:
        print(f"{item.start_time:%H:%M}-{item.end_time:%H:%M}  "
              f"{item.pet_name:<8} {item.task.title} ({item.task.duration_minutes} min)")
        print(f"             why: {item.reason}")
    for task, reason in skipped:
        print(f"  skipped {task.title}: {reason}")
    total = sum(i.task.duration_minutes for i in items)
    print(f"Total: {total} of {scheduler.owner.available_minutes} minutes")


def normal_day(today: date) -> None:
    owner, biscuit, mochi = build_owner(90)
    biscuit.add_task(Task("Morning walk", 30, Priority.HIGH, time(8, 0)))
    biscuit.add_task(Task("Grooming", 25, Priority.LOW))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH, time(9, 0)))
    mochi.add_task(Task("Medication", 5, Priority.HIGH, time(12, 30)))
    mochi.add_task(Task("Laser pointer play", 20, Priority.MEDIUM, time(18, 0)))
    show("1. Normal day", Scheduler(owner), today)


def overloaded_day(today: date) -> None:
    owner, biscuit, mochi = build_owner(40)
    biscuit.add_task(Task("Long hike", 60, Priority.HIGH))
    biscuit.add_task(Task("Teeth brushing", 10, Priority.MEDIUM))
    biscuit.add_task(Task("Nail trim", 15, Priority.MEDIUM))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH))
    mochi.add_task(Task("Missed vet meds", 10, Priority.MEDIUM,
                        start_date=today - timedelta(days=2)))  # overdue -> boosted
    show("2. Overloaded day (40-min budget, knapsack + overdue boost)",
         Scheduler(owner), today)


def colliding_day(today: date) -> None:
    owner, biscuit, mochi = build_owner(180)
    walk = Task("Morning walk", 30, Priority.HIGH, time(8, 0))
    biscuit.add_task(walk)
    mochi.add_task(Task("Brushing", 10, Priority.LOW, time(8, 15)))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH, time(9, 0)))
    # Must come right after Feeding, even though it asked for 08:00.
    mochi.add_task(Task("Medication", 5, Priority.HIGH, time(8, 0),
                        after=mochi.tasks[-1].id))
    biscuit.add_task(Task("Dinner", 15, Priority.HIGH, earliest=time(17, 0)))
    show("3. Colliding times, dependency, 5-min buffer, time window",
         Scheduler(owner, buffer_minutes=5, max_drift_minutes=90), today)


def main() -> None:
    today = date.today()
    normal_day(today)
    overloaded_day(today)
    colliding_day(today)


if __name__ == "__main__":
    main()
