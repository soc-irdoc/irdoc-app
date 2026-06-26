# Tasks

The Tasks tab inside an incident workspace is a checklist of action items for the investigation. Tasks track what needs to be done, who is doing it, and where it stands. The tab header shows an "X of Y done" progress count, which also appears in the incident header.

---

## Task Fields

| Field | Description |
|---|---|
| Title | Short description of the action item. Required. |
| Description | Additional detail or instructions. Optional. |
| Phase | Free-text grouping label (e.g. `Containment`, `Eradication`, `Recovery`). Optional. |
| Priority | critical, high, medium, or low. Displayed with a color indicator. |
| Assigned to | The user responsible for this task. Optional. |
| Status | open, in_progress, or completed. |

---

## Adding a Task

> **Analyst role or higher required.**

1. Open the **Tasks** tab in the incident workspace
2. Click **Add Task**
3. Enter the task title and any optional fields
4. Press `Enter` or click **Save**

The task appears at the bottom of the list.

---

## Completing a Task

Click the checkbox to the left of a task to mark it completed. The status moves to `completed` and the progress counter updates.

- Analysts can mark their own tasks complete
- Senior analysts can mark any task complete

---

## Editing a Task

Click any field on a task row to edit it inline:

- **Assignee** — click the assignee field to open a user picker
- **Priority** — click the priority badge to cycle through priority levels
- **Phase, description** — click to edit inline

> **Senior Analyst role or higher required** to edit tasks assigned to other users.

---

## Reordering Tasks

Drag a task by its handle (the grip icon on the left) to reorder it within the list. Order is saved automatically.

---

## Deleting a Task

> **Senior Analyst role or higher required.**

Hover over a task row and click the delete icon that appears. Confirm when prompted. Deletion is permanent.

---

## Tasks from Templates

When an incident is created using a template, the template's task checklist is pre-populated in the Tasks tab. These tasks behave identically to manually created tasks — they can be edited, reassigned, reordered, or deleted after the incident is created.

---

## Role Summary

| Action | Minimum role |
|---|---|
| View tasks | viewer |
| Create a task | analyst |
| Edit your own task | analyst |
| Mark your own task complete | analyst |
| Edit or delete any task | senior_analyst |
| Mark any task complete | senior_analyst |
