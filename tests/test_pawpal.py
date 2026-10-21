from datetime import date

from pawpal_system import Pet, Task


def test_mark_complete_changes_task_status():
    today = date(2026, 10, 20)
    task = Task("Morning walk", 30)

    assert task.is_due(today)

    task.mark_complete(today)

    assert task.last_completed == today
    assert not task.is_due(today)


def test_adding_task_increases_pet_task_count():
    pet = Pet("Biscuit", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", 10))
    assert len(pet.tasks) == 1

    pet.add_task(Task("Grooming", 25))
    assert len(pet.tasks) == 2
