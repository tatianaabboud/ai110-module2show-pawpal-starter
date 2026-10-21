# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Output from running `python main.py`, which prints three scenarios: a normal day, an overloaded day (knapsack choice plus the overdue boost), and a day with colliding times (conflict warnings, a dependency, a buffer and a time window):

```

1. Normal day
============================================================
08:00-08:30  Biscuit  Morning walk (30 min)
             why: high priority; scheduled at its preferred time
08:30-08:55  Biscuit  Grooming (25 min)
             why: low priority; placed in the earliest free slot
09:00-09:10  Mochi    Feeding (10 min)
             why: high priority; scheduled at its preferred time
12:30-12:35  Mochi    Medication (5 min)
             why: high priority; scheduled at its preferred time
18:00-18:20  Mochi    Laser pointer play (20 min)
             why: medium priority; scheduled at its preferred time
Total: 90 of 90 minutes

2. Overloaded day (40-min budget, knapsack + overdue boost)
============================================================
08:00-08:10  Biscuit  Teeth brushing (10 min)
             why: medium priority; placed in the earliest free slot
08:10-08:20  Mochi    Feeding (10 min)
             why: high priority; placed in the earliest free slot
08:20-08:30  Mochi    Missed vet meds (10 min)
             why: medium priority (raised a level: overdue); placed in the earliest free slot
  skipped Long hike: needs 60 min but the whole daily budget is 40 min
  skipped Nail trim: left out so the 40-min daily budget goes to higher-value tasks
Total: 30 of 40 minutes

3. Colliding times, dependency, 5-min buffer, time window
============================================================
WARNING: Conflict (different pets): Biscuit's 'Morning walk' (08:00-08:30) overlaps Mochi's 'Medication' (08:00-08:05)
WARNING: Conflict (different pets): Biscuit's 'Morning walk' (08:00-08:30) overlaps Mochi's 'Brushing' (08:15-08:25)
08:00-08:30  Biscuit  Morning walk (30 min)
             why: high priority; scheduled at its preferred time
08:35-08:45  Mochi    Brushing (10 min)
             why: low priority; preferred time 08:15 was taken, moved to 08:35
09:00-09:10  Mochi    Feeding (10 min)
             why: high priority; scheduled at its preferred time
09:15-09:20  Mochi    Medication (5 min)
             why: high priority; follows 'Feeding'; preferred time 08:00 was taken, moved to 09:15
17:00-17:15  Biscuit  Dinner (15 min)
             why: high priority; placed in the earliest free slot
Total: 70 of 180 minutes
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output (`pytest -v`):

```
============================= test session starts =============================
collected 31 items

tests/test_pawpal.py::test_mark_complete_changes_task_status PASSED      [  3%]
tests/test_pawpal.py::test_adding_task_increases_pet_task_count PASSED   [  6%]
tests/test_pawpal.py::test_sort_by_time_orders_hhmm_and_puts_none_last PASSED [  9%]
tests/test_pawpal.py::test_sort_by_time_all_none_keeps_order PASSED      [ 12%]
tests/test_pawpal.py::test_generate_plan_places_tasks_in_preferred_time_order PASSED [ 16%]
tests/test_pawpal.py::test_filter_tasks_by_pet_name_is_case_insensitive PASSED [ 19%]
tests/test_pawpal.py::test_filter_tasks_by_completion_status PASSED      [ 22%]
tests/test_pawpal.py::test_filter_tasks_combines_filters_and_none_returns_all PASSED [ 25%]
tests/test_pawpal.py::test_completing_daily_task_creates_next_day_occurrence PASSED [ 29%]
tests/test_pawpal.py::test_completing_weekly_task_creates_occurrence_seven_days_later PASSED [ 32%]
tests/test_pawpal.py::test_completing_once_task_creates_no_new_occurrence PASSED [ 35%]
tests/test_pawpal.py::test_generate_plan_skips_completed_and_future_occurrences PASSED [ 38%]
tests/test_pawpal.py::test_find_conflicts_flags_same_pet_overlap PASSED  [ 41%]
tests/test_pawpal.py::test_find_conflicts_flags_different_pets_at_same_time PASSED [ 45%]
tests/test_pawpal.py::test_find_conflicts_ignores_back_to_back_untimed_and_not_due PASSED [ 48%]
tests/test_pawpal.py::test_knapsack_beats_greedy_priority_order PASSED   [ 51%]
tests/test_pawpal.py::test_knapsack_prefers_fewer_minutes_on_equal_value PASSED [ 54%]
tests/test_pawpal.py::test_task_longer_than_budget_is_skipped_with_reason PASSED [ 58%]
tests/test_pawpal.py::test_find_slot_picks_nearest_gap_before_or_after PASSED [ 61%]
tests/test_pawpal.py::test_find_slot_respects_buffer_and_bounds PASSED   [ 64%]
tests/test_pawpal.py::test_buffer_minutes_adds_gap_between_tasks PASSED  [ 67%]
tests/test_pawpal.py::test_max_drift_skips_task_that_would_move_too_far PASSED [ 70%]
tests/test_pawpal.py::test_overdue_task_is_boosted_when_budget_is_tight PASSED [ 74%]
tests/test_pawpal.py::test_day_end_and_latest_limit_when_tasks_can_run PASSED [ 77%]
tests/test_pawpal.py::test_earliest_pushes_start_of_untimed_task PASSED  [ 80%]
tests/test_pawpal.py::test_task_rejects_inverted_window_and_self_dependency PASSED [ 83%]
tests/test_pawpal.py::test_dependency_places_task_after_predecessor PASSED [ 87%]
tests/test_pawpal.py::test_dependency_on_unscheduled_task_skips_dependent PASSED [ 90%]
tests/test_pawpal.py::test_dependency_on_completed_task_is_ignored PASSED [ 93%]
tests/test_pawpal.py::test_circular_dependency_is_reported_not_crashed PASSED [ 96%]
tests/test_pawpal.py::test_untimed_tasks_are_grouped_by_pet PASSED       [100%]

============================= 31 passed in 0.06s ==============================
```

## 📐 Smarter Scheduling

All of this lives in [pawpal_system.py](pawpal_system.py) and is wired into the Streamlit UI in [app.py](app.py).

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting by time | `Scheduler.sort_by_time()` | Orders tasks by preferred time; tasks with no time go last |
| Filtering | `Scheduler.filter_tasks()` | By pet name and/or completion status |
| Conflict detection | `Scheduler.find_conflicts()` | Warns about overlapping preferred times; never blocks scheduling |
| Recurring tasks | `Pet.complete_task()`, `Task.is_due()` | Completing a daily/weekly task creates the next occurrence |
| Choosing tasks | `Scheduler._select_tasks()` | Knapsack: best-valued tasks that fit the time budget |
| Placing tasks | `Scheduler._place()`, `Scheduler._find_slot()` | Nearest free slot, honoring windows, buffer and dependencies |
| Overdue boost | `Scheduler._effective_priority()`, `Task.is_overdue()` | Missed tasks move up one priority level |

### Sorting

`Scheduler.sort_by_time(tasks)` returns tasks ordered by `preferred_time`, earliest first. Its key is a lambda that turns each time into a zero-padded `"HH:MM"` string, which sorts chronologically as plain text. Tasks without a preferred time sort last, and the sort is stable, so ties keep their original order.

`generate_plan` uses it to decide placement order, so an earlier preferred time gets its slot first. The task list in the UI offers it as **Sort by → Preferred time**.

### Filtering

`Scheduler.filter_tasks(pet_name=None, completed=None)` returns `(pet, task)` pairs.

- `pet_name` matches case-insensitively; `None` means all pets.
- `completed=True` returns finished tasks, `False` returns open ones, `None` returns both.
- The two filters combine (AND).

The UI exposes these as **Filter by pet** and **Filter by status** (All / Pending / Completed).

### Conflict detection

`Scheduler.find_conflicts(on_date)` is a lightweight check that returns **warning messages instead of raising**. It takes the tasks due that day that have a preferred time, sorts them by start, and compares every earlier/later pair. A pair conflicts when the later task starts before the earlier one ends (start + duration), whether the tasks are for the same pet or different pets. Back-to-back tasks are not conflicts, and tasks without a preferred time are never compared.

Example message:

```
Conflict (different pets): Biscuit's 'Morning walk' (08:00-08:30) overlaps Mochi's 'Brushing' (08:15-08:25)
```

It only warns. `generate_plan` still produces a valid, non-overlapping plan by moving the later task to the nearest free slot, and the plan's "why" column says it was moved. The UI shows the warnings above the task list, and `main.py` prints them before the schedule.

### Recurring tasks

Each `Task` is one occurrence. `Pet.complete_task(task, on_date)` marks it done and, for `daily` or `weekly` tasks, adds a **new** task (same details, fresh `id`, not completed) whose `start_date` is `on_date` + 1 day (daily) or + 7 days (weekly). A `once` task creates nothing and returns `None`.

`Task.is_due(on_date)` is true only while a task is not completed and its `start_date` has arrived, so a finished occurrence never comes back and the next one stays hidden until its day. Completed tasks remain on the pet as history. The UI's **Mark complete** button calls `complete_task` and reports when the next occurrence is due.

### How the daily plan is built

`Scheduler.generate_plan(on_date)` ties it together:

1. **Choose:** `_select_tasks` runs a 0/1 knapsack so the plan holds the most value within the owner's minutes (HIGH counts 9, MEDIUM 3, LOW 1; ties favor fewer minutes). Tasks left out are returned with a reason.
2. **Order:** a pet's tasks are grouped together, then ordered with `sort_by_time`.
3. **Place:** `_place` finds the free slot nearest each task's preferred time (earlier or later) through `_find_slot`. It respects the day's start and end, each task's `earliest` and `latest` window, an optional `buffer_minutes` gap, an optional `max_drift_minutes` cap, and `Task.after` dependencies. A task that cannot be placed is skipped with a reason, and a circular dependency is reported instead of crashing.

Overdue tasks (due on an earlier day and still open) are raised one priority level when choosing, and the plan says so in the "why" text.

### Tradeoffs and known limitations

- Choosing and placing are separate steps, so a task picked by the knapsack can fail placement (for example, an impossible time window) and its time is not given to a lower-priority task.
- Conflict detection compares only preferred times, not the final plan or the time budget.
- Known bug: `find_conflicts` raises `ValueError` if an overlapping task would end after midnight (for example a 30-minute task at 23:45), because the end time can't be formatted.
- A task's `after` dependency points at one specific occurrence; it does not follow a recurring task's next occurrence.
- A weekly task's next date is counted from the day it was completed, not its original schedule.

## 📸 Demo Walkthrough

Run the app with `streamlit run app.py`, then:

1. **Set up the owner.** Enter your name and how many minutes you have today under *Owner & Pets*.
2. **Add pets.** Type a pet name, pick a species and click **Add pet**. Each pet appears in the pets table with its task count.
3. **Add tasks.** Choose a pet, then enter a title, duration and priority. Optionally set a preferred time (`HH:MM`), a "Not before" / "Finish by" window, how often it repeats (daily, weekly or once) and a task it must come after. Click **Add task**. Bad times such as `99:99` show an error instead of being added.
4. **Watch for conflict warnings.** If two tasks want overlapping times, a yellow warning names both tasks and their times, and notes that the schedule will move the later one.
5. **Explore the task list.** Filter by pet or status (All / Pending / Completed), and sort by time added or preferred time. The table shows each task's time, repeat setting, due date and overdue flag.
6. **Complete a task.** Pick a task under *Mark a task complete* and click **Mark complete**. For a daily or weekly task, the app confirms when the next occurrence is due, and the new task appears in the list.
7. **Tune the scheduler (optional).** Open *Scheduling options* to set when your day starts and ends, a buffer between tasks, and a cap on how far a task may move from its preferred time.
8. **Generate the schedule.** Click **Generate schedule**. The table shows each task's time, pet and a plain-English "why". Tasks that didn't make the plan are listed below with the reason, such as "left out so the budget goes to higher-value tasks".

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
