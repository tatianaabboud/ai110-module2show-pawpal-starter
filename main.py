"""Temporary CLI testing ground for the PawPal+ logic layer."""

from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def main() -> None:
    owner = Owner("Jordan", available_minutes=90)

    biscuit = Pet("Biscuit", "dog", age=4)
    mochi = Pet("Mochi", "cat", age=2)
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    biscuit.add_task(Task("Morning walk", 30, Priority.HIGH, time(8, 0)))
    biscuit.add_task(Task("Grooming", 25, Priority.LOW))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH, time(9, 0)))
    mochi.add_task(Task("Medication", 5, Priority.HIGH, time(12, 30)))
    mochi.add_task(Task("Laser pointer play", 20, Priority.MEDIUM, time(18, 0)))

    today = date.today()
    items, skipped = Scheduler(owner).generate_plan(today)

    print(f"Today's Schedule for {owner.name} ({today:%A, %b %d})")
    print("=" * 50)
    for item in items:
        print(f"{item.start_time:%H:%M}-{item.end_time:%H:%M}  "
              f"{item.pet_name:<8} {item.task.title} "
              f"({item.task.duration_minutes} min)")
        print(f"             why: {item.reason}")

    if skipped:
        print("\nSkipped:")
        for task, reason in skipped:
            print(f"  - {task.title}: {reason}")

    total = sum(i.task.duration_minutes for i in items)
    print(f"\nTotal: {total} of {owner.available_minutes} minutes")


if __name__ == "__main__":
    main()
