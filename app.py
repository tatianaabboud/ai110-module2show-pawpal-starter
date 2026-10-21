from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner & Pets")

# st.session_state is a dict-like "vault" that survives reruns. Only create the
# Owner if the vault doesn't already hold one; otherwise reuse the stored object.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
owner = st.session_state.owner

col_a, col_b = st.columns(2)
with col_a:
    owner.name = st.text_input("Owner name", value=owner.name)
with col_b:
    owner.available_minutes = int(
        st.number_input(
            "Time available today (minutes)",
            min_value=1, max_value=1440, value=owner.available_minutes,
        )
    )

col_p1, col_p2 = st.columns(2)
with col_p1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_p2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    if not pet_name.strip():
        st.error("Pet name is required.")
    elif any(p.name == pet_name.strip() for p in owner.pets):
        st.warning(f"{pet_name} is already on your list.")
    else:
        owner.add_pet(Pet(name=pet_name.strip(), species=species))
        st.success(f"Added {pet_name}.")

if owner.pets:
    st.write("Your pets:")
    st.table([{"name": p.name, "species": p.species, "tasks": len(p.tasks)} for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")

def parse_hhmm(text: str):
    """Return a time for "HH:MM" text, None for blank; raise ValueError if malformed."""
    text = text.strip()
    return datetime.strptime(text, "%H:%M").time() if text else None


st.markdown("### Tasks")

if owner.pets:
    col0, col1, col2, col3 = st.columns([2, 3, 2, 2])
    with col0:
        task_pet = st.selectbox("For pet", [p.name for p in owner.pets])
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5 = st.columns(2)
    with col4:
        time_text = st.text_input(
            "Preferred time (HH:MM, optional)", value="",
            help="Leave blank to let PawPal+ pick the earliest free slot.",
        )
    with col5:
        frequency = st.selectbox("Repeats", ["daily", "weekly", "once"])

    col6, col7, col8 = st.columns(3)
    with col6:
        earliest_text = st.text_input("Not before (HH:MM, optional)", value="")
    with col7:
        latest_text = st.text_input("Finish by (HH:MM, optional)", value="")
    with col8:
        open_tasks = {t.id: f"{p.name}: {t.title}"
                      for p, t in owner.get_all_tasks() if t.last_completed is None}
        after_id = st.selectbox(
            "Do after (optional)", [""] + list(open_tasks),
            format_func=lambda i: open_tasks.get(i, "(no dependency)"),
        )

    if st.button("Add task"):
        try:
            preferred = parse_hhmm(time_text)
            earliest = parse_hhmm(earliest_text)
            latest = parse_hhmm(latest_text)
            target = next(p for p in owner.pets if p.name == task_pet)
            target.add_task(
                Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=Priority[priority.upper()],
                    preferred_time=preferred,
                    frequency=frequency,
                    earliest=earliest,
                    latest=latest,
                    after=after_id or None,
                )
            )
            st.session_state.flash = f"Added '{task_title}' for {task_pet}."
            st.rerun()  # refresh the "Do after" list so the new task appears
        except ValueError as err:
            st.error(f"Could not add task: {err}. Times must look like HH:MM, e.g. 08:30.")
else:
    st.caption("Add a pet first to start adding tasks.")

scheduler = Scheduler(owner)
today = date.today()

if owner.get_all_tasks():
    for warning in scheduler.find_conflicts(today):
        st.warning(f"{warning}. The schedule will move the later task to the next free slot.")
    st.write("Current tasks:")
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    f1, f2, f3 = st.columns(3)
    with f1:
        pet_filter = st.selectbox("Filter by pet", ["All pets"] + [p.name for p in owner.pets])
    with f2:
        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"])
    with f3:
        sort_choice = st.selectbox("Sort by", ["Time added", "Preferred time"])

    shown = scheduler.filter_tasks(
        pet_name=None if pet_filter == "All pets" else pet_filter,
        completed={"All": None, "Pending": False, "Completed": True}[status_filter],
    )
    if sort_choice == "Preferred time":
        pet_for = {t.id: p for p, t in shown}
        shown = [(pet_for[t.id], t) for t in scheduler.sort_by_time([t for _, t in shown])]

    if shown:
        titles_by_id = {t.id: t.title for _, t in owner.get_all_tasks()}
        st.table(
            [
                {
                    "pet": p.name,
                    "title": t.title,
                    "time": f"{t.preferred_time:%H:%M}" if t.preferred_time else "any",
                    "duration_minutes": t.duration_minutes,
                    "priority": t.priority.name.lower(),
                    "repeats": t.frequency,
                    "window": (f"{t.earliest:%H:%M}" if t.earliest else "") + "-"
                              + (f"{t.latest:%H:%M}" if t.latest else "")
                              if t.earliest or t.latest else "",
                    "after": titles_by_id.get(t.after, "") if t.after else "",
                    "overdue": "yes" if t.is_overdue(today) else "",
                    "due": f"{t.start_date:%b %d}",
                    "done": f"{t.last_completed:%b %d}" if t.last_completed else "no",
                }
                for p, t in shown
            ]
        )
        # Only occurrences due today can be completed; future ones are queued.
        due_now = [(p, t) for p, t in shown if t.is_due(today)]
        if due_now:
            labels = {t.id: f"{p.name}: {t.title}" for p, t in due_now}
            to_complete = st.selectbox(
                "Mark a task complete", list(labels), format_func=labels.get
            )
            if st.button("Mark complete"):
                pet, task = next((p, t) for p, t in due_now if t.id == to_complete)
                nxt = pet.complete_task(task, today)
                st.session_state.flash = (
                    f"Completed '{task.title}'. Next occurrence scheduled for "
                    f"{nxt.start_date:%A, %b %d}." if nxt
                    else f"Completed '{task.title}'."
                )
                st.rerun()
    else:
        st.info("No tasks match those filters.")
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption(
    "Picks the highest-value tasks that fit your time budget (overdue tasks get a "
    "boost), groups each pet's tasks, then places them nearest their preferred time."
)

with st.expander("Scheduling options"):
    o1, o2 = st.columns(2)
    with o1:
        day_start = st.time_input("Day starts", value=time(8, 0), step=900)
        buffer_minutes = int(st.number_input("Buffer between tasks (min)", 0, 60, 0))
    with o2:
        day_end = st.time_input("Day ends", value=time(22, 0), step=900)
        max_drift = int(st.number_input(
            "Max shift from preferred time (min, 0 = unlimited)", 0, 720, 0))

if st.button("Generate schedule"):
    if not owner.get_all_tasks():
        st.warning("Add at least one task first.")
    else:
        plan_scheduler = Scheduler(
            owner, day_start=day_start, day_end=day_end,
            buffer_minutes=buffer_minutes, max_drift_minutes=max_drift or None,
        )
        items, skipped = plan_scheduler.generate_plan(today)
        if items:
            st.success(f"Scheduled {len(items)} task(s) for today.")
            st.table(
                [
                    {
                        "time": f"{i.start_time:%H:%M}-{i.end_time:%H:%M}",
                        "pet": i.pet_name,
                        "task": i.task.title,
                        "why": i.reason,
                    }
                    for i in items
                ]
            )
        else:
            st.info("Nothing is due today.")
        for task, reason in skipped:
            st.warning(f"Skipped '{task.title}': {reason}")
