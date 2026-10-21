from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


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


def test_sort_by_time_orders_hhmm_and_puts_none_last():
    scheduler = Scheduler(Owner("Jordan"))
    evening = Task("Play", 20, preferred_time=time(18, 0))
    anytime = Task("Grooming", 25)
    early = Task("Walk", 30, preferred_time=time(8, 5))
    noon = Task("Meds", 5, preferred_time=time(12, 30))

    result = scheduler.sort_by_time([evening, anytime, noon, early])

    assert [t.title for t in result] == ["Walk", "Meds", "Play", "Grooming"]


def test_sort_by_time_all_none_keeps_order():
    scheduler = Scheduler(Owner("Jordan"))
    a, b = Task("A", 5), Task("B", 5)

    assert scheduler.sort_by_time([a, b]) == [a, b]
    assert scheduler.sort_by_time([]) == []


def test_generate_plan_places_tasks_in_preferred_time_order():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Mochi", "cat")
    owner.add_pet(pet)
    # Added out of time order; the HIGH-priority task has the later time.
    pet.add_task(Task("Play", 20, Priority.LOW, time(9, 0)))
    pet.add_task(Task("Meds", 30, Priority.HIGH, time(9, 15)))
    pet.add_task(Task("Grooming", 25, Priority.MEDIUM))

    items, skipped = Scheduler(owner).generate_plan(date(2026, 10, 20))

    assert not skipped
    assert [(i.task.title, i.start_time) for i in items] == [
        ("Grooming", time(8, 0)),
        ("Play", time(9, 0)),
        ("Meds", time(9, 20)),  # wanted 9:15, shifted past Play (earlier time wins)
    ]


def _filter_fixture():
    owner = Owner("Jordan")
    biscuit, mochi = Pet("Biscuit", "dog"), Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    walk, groom = Task("Walk", 30), Task("Grooming", 25, frequency="once")
    biscuit.add_task(walk)
    biscuit.add_task(groom)
    mochi.add_task(Task("Feeding", 10))
    mochi.add_task(Task("Meds", 5))
    biscuit.complete_task(walk, date(2026, 10, 20))  # also spawns tomorrow's walk
    groom.mark_complete(date(2026, 10, 1))
    return Scheduler(owner)


def test_filter_tasks_by_pet_name_is_case_insensitive():
    scheduler = _filter_fixture()

    titles = [t.title for _, t in scheduler.filter_tasks(pet_name="mochi")]

    assert titles == ["Feeding", "Meds"]
    assert scheduler.filter_tasks(pet_name="Nobody") == []


def test_filter_tasks_by_completion_status():
    scheduler = _filter_fixture()

    done = [t.title for _, t in scheduler.filter_tasks(completed=True)]
    pending = [t.title for _, t in scheduler.filter_tasks(completed=False)]

    assert done == ["Walk", "Grooming"]
    assert pending == ["Walk", "Feeding", "Meds"]  # first Walk = the spawned occurrence


def test_filter_tasks_combines_filters_and_none_returns_all():
    scheduler = _filter_fixture()

    combo = scheduler.filter_tasks(pet_name="Biscuit", completed=False)

    assert [t.title for _, t in combo] == ["Walk"]
    assert len(scheduler.filter_tasks()) == 5


def test_completing_daily_task_creates_next_day_occurrence():
    pet = Pet("Biscuit", "dog")
    walk = Task("Walk", 30, Priority.HIGH, time(8, 0), frequency="daily")
    pet.add_task(walk)
    today = date(2026, 10, 20)

    nxt = pet.complete_task(walk, today)

    assert walk.last_completed == today and not walk.is_due(today)
    assert nxt is not None and nxt is not walk and nxt.id != walk.id
    assert nxt.start_date == date(2026, 10, 21)
    assert nxt.last_completed is None
    assert (nxt.title, nxt.duration_minutes, nxt.priority, nxt.preferred_time) == (
        "Walk", 30, Priority.HIGH, time(8, 0))
    assert pet.tasks == [walk, nxt]
    assert not nxt.is_due(today) and nxt.is_due(date(2026, 10, 21))
    # The finished occurrence never comes back.
    assert not walk.is_due(date(2026, 10, 21))


def test_completing_weekly_task_creates_occurrence_seven_days_later():
    pet = Pet("Mochi", "cat")
    bath = Task("Bath", 20, frequency="weekly")
    pet.add_task(bath)

    nxt = pet.complete_task(bath, date(2026, 10, 20))

    assert nxt.start_date == date(2026, 10, 27)
    assert not nxt.is_due(date(2026, 10, 26)) and nxt.is_due(date(2026, 10, 27))


def test_completing_once_task_creates_no_new_occurrence():
    pet = Pet("Biscuit", "dog")
    vet = Task("Vet visit", 60, frequency="once")
    pet.add_task(vet)

    assert pet.complete_task(vet, date(2026, 10, 20)) is None
    assert pet.tasks == [vet]


def test_generate_plan_skips_completed_and_future_occurrences():
    owner = Owner("Jordan")
    pet = Pet("Biscuit", "dog")
    owner.add_pet(pet)
    walk = Task("Walk", 30)
    pet.add_task(walk)
    today = date(2026, 10, 20)
    pet.complete_task(walk, today)

    today_items, _ = Scheduler(owner).generate_plan(today)
    tomorrow_items, _ = Scheduler(owner).generate_plan(date(2026, 10, 21))

    assert today_items == []
    assert [i.task.title for i in tomorrow_items] == ["Walk"]


def _conflict_owner():
    owner = Owner("Jordan")
    biscuit, mochi = Pet("Biscuit", "dog"), Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return owner, biscuit, mochi


def test_find_conflicts_flags_same_pet_overlap():
    owner, biscuit, _ = _conflict_owner()
    biscuit.add_task(Task("Walk", 30, preferred_time=time(8, 0)))
    biscuit.add_task(Task("Grooming", 20, preferred_time=time(8, 15)))

    warnings = Scheduler(owner).find_conflicts(date(2026, 10, 20))

    assert len(warnings) == 1
    assert "same pet" in warnings[0]
    assert "'Walk'" in warnings[0] and "'Grooming'" in warnings[0]


def test_find_conflicts_flags_different_pets_at_same_time():
    owner, biscuit, mochi = _conflict_owner()
    biscuit.add_task(Task("Walk", 30, preferred_time=time(9, 0)))
    mochi.add_task(Task("Feeding", 10, preferred_time=time(9, 0)))

    warnings = Scheduler(owner).find_conflicts(date(2026, 10, 20))

    assert len(warnings) == 1 and "different pets" in warnings[0]


def test_find_conflicts_ignores_back_to_back_untimed_and_not_due():
    owner, biscuit, mochi = _conflict_owner()
    biscuit.add_task(Task("Walk", 30, preferred_time=time(8, 0)))
    mochi.add_task(Task("Feeding", 10, preferred_time=time(8, 30)))  # starts as Walk ends
    mochi.add_task(Task("Play", 20))                                  # no preferred time
    future = Task("Bath", 30, preferred_time=time(8, 10),
                  start_date=date(2026, 10, 25))                      # not due yet
    biscuit.add_task(future)

    assert Scheduler(owner).find_conflicts(date(2026, 10, 20)) == []
    assert Scheduler(Owner("Empty")).find_conflicts(date(2026, 10, 20)) == []


# ---- planning improvements -------------------------------------------------

DAY = date(2026, 10, 20)


def _plan(owner, **kwargs):
    return Scheduler(owner, **kwargs).generate_plan(DAY)


def _owner_with(*tasks, minutes=120, pets=("Biscuit",)):
    owner = Owner("Jordan", available_minutes=minutes)
    made = [Pet(n, "dog") for n in pets]
    for p in made:
        owner.add_pet(p)
    for t in tasks:
        made[0].add_task(t)
    return owner


def test_knapsack_beats_greedy_priority_order():
    # Greedy-by-priority would take the 60-min HIGH task (value 9) and fill the
    # budget; four 15-min MEDIUM tasks are worth 12, so the knapsack picks them.
    hike = Task("Long hike", 60, Priority.HIGH)
    chores = [Task(f"Chore {i}", 15, Priority.MEDIUM) for i in range(4)]
    owner = _owner_with(hike, *chores, minutes=60)

    items, skipped = _plan(owner)

    assert sorted(i.task.title for i in items) == [f"Chore {i}" for i in range(4)]
    assert [t.title for t, _ in skipped] == ["Long hike"]


def test_knapsack_prefers_fewer_minutes_on_equal_value():
    long_walk = Task("Long walk", 40, Priority.HIGH)
    short_walk = Task("Short walk", 15, Priority.HIGH)
    owner = _owner_with(long_walk, short_walk, minutes=40)

    items, _ = _plan(owner)

    assert [i.task.title for i in items] == ["Short walk"]


def test_task_longer_than_budget_is_skipped_with_reason():
    owner = _owner_with(Task("Marathon", 200, Priority.HIGH), minutes=60)

    items, skipped = _plan(owner)

    assert items == [] and "whole daily budget" in skipped[0][1]


def test_find_slot_picks_nearest_gap_before_or_after():
    busy = [(600, 660)]  # 10:00-11:00
    assert Scheduler._find_slot(busy, 650, 30, 480, 1439) == 660   # after is closer
    assert Scheduler._find_slot(busy, 605, 30, 480, 1439) == 570   # before is closer


def test_find_slot_respects_buffer_and_bounds():
    busy = [(600, 630)]
    # With a 10-min buffer the task must start at 640 or end by 590 (start 560).
    assert Scheduler._find_slot(busy, 600, 30, 480, 1439, buffer=10) == 560
    assert Scheduler._find_slot(busy, 600, 30, 480, 630, buffer=10) == 560
    assert Scheduler._find_slot([(480, 1439)], 480, 10, 480, 1439) is None


def test_buffer_minutes_adds_gap_between_tasks():
    owner = _owner_with(
        Task("Walk", 30, Priority.HIGH, time(8, 0)),
        Task("Feed", 10, Priority.HIGH, time(8, 30)),
    )

    items, _ = _plan(owner, buffer_minutes=5)

    assert [(i.task.title, i.start_time) for i in items] == [
        ("Walk", time(8, 0)), ("Feed", time(8, 35))]


def test_max_drift_skips_task_that_would_move_too_far():
    owner = _owner_with(
        Task("Walk", 60, Priority.HIGH, time(9, 0)),
        Task("Feed", 10, Priority.MEDIUM, time(9, 30)),
    )

    items, skipped = _plan(owner, max_drift_minutes=15)

    assert [i.task.title for i in items] == ["Walk"]
    assert "over the 15-min limit" in skipped[0][1]


def test_overdue_task_is_boosted_when_budget_is_tight():
    overdue = Task("Meds", 30, Priority.MEDIUM, start_date=date(2026, 10, 18))
    fresh = Task("Play", 30, Priority.MEDIUM)
    owner = _owner_with(fresh, overdue, minutes=30)

    items, skipped = _plan(owner)

    assert [i.task.title for i in items] == ["Meds"]
    assert "overdue" in items[0].reason
    assert [t.title for t, _ in skipped] == ["Play"]


def test_day_end_and_latest_limit_when_tasks_can_run():
    owner = _owner_with(
        Task("Late walk", 30, Priority.HIGH, time(8, 0), latest=time(8, 20)),
        Task("Evening play", 30, Priority.HIGH),
    )

    items, skipped = _plan(owner, day_end=time(8, 45))

    assert [i.task.title for i in items] == ["Evening play"]
    assert "no free 30-min slot" in skipped[0][1]


def test_earliest_pushes_start_of_untimed_task():
    owner = _owner_with(Task("Walk", 20, Priority.HIGH, earliest=time(10, 0)))

    items, _ = _plan(owner)

    assert items[0].start_time == time(10, 0)


def test_task_rejects_inverted_window_and_self_dependency():
    import pytest
    with pytest.raises(ValueError):
        Task("Bad", 10, earliest=time(10, 0), latest=time(9, 0))
    with pytest.raises(ValueError):
        t = Task("Loop", 10)
        Task("Loop", 10, after=t.id, id=t.id)


def test_dependency_places_task_after_predecessor():
    feed = Task("Feed", 10, Priority.HIGH, time(9, 0))
    meds = Task("Meds", 5, Priority.HIGH, time(8, 0), after=feed.id)  # wants 08:00
    owner = _owner_with(feed, meds)

    items, skipped = _plan(owner)

    by_title = {i.task.title: i for i in items}
    assert by_title["Feed"].start_time == time(9, 0)
    assert by_title["Meds"].start_time == time(9, 10)  # right after Feed
    assert "follows 'Feed'" in by_title["Meds"].reason
    assert not skipped


def test_dependency_on_unscheduled_task_skips_dependent():
    feed = Task("Feed", 50, Priority.LOW)
    meds = Task("Meds", 5, Priority.HIGH, after=feed.id)
    owner = _owner_with(feed, meds, minutes=20)

    items, skipped = _plan(owner)

    assert items == []
    assert any("depends on 'Feed'" in r for _, r in skipped)


def test_dependency_on_completed_task_is_ignored():
    pet = Pet("Biscuit", "dog")
    owner = Owner("Jordan")
    owner.add_pet(pet)
    done = Task("Feed", 10, frequency="once")
    pet.add_task(done)
    pet.complete_task(done, DAY)
    pet.add_task(Task("Meds", 5, after=done.id))

    items, skipped = _plan(owner)

    assert [i.task.title for i in items] == ["Meds"] and not skipped


def test_circular_dependency_is_reported_not_crashed():
    a, b = Task("A", 10), Task("B", 10)
    a.after, b.after = b.id, a.id
    owner = _owner_with(a, b)

    items, skipped = _plan(owner)

    assert items == []
    assert {t.title for t, _ in skipped} == {"A", "B"}
    assert all("circular" in r for _, r in skipped)


def test_untimed_tasks_are_grouped_by_pet():
    owner = Owner("Jordan", available_minutes=200)
    biscuit, mochi = Pet("Biscuit", "dog"), Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    # Priority order would interleave pets (HIGH, HIGH, MEDIUM, MEDIUM).
    mochi.add_task(Task("M1", 10, Priority.HIGH))
    biscuit.add_task(Task("B1", 10, Priority.HIGH))
    mochi.add_task(Task("M2", 10, Priority.MEDIUM))
    biscuit.add_task(Task("B2", 10, Priority.MEDIUM))

    items, _ = _plan(owner)

    assert [i.pet_name for i in items] == ["Biscuit", "Biscuit", "Mochi", "Mochi"]
