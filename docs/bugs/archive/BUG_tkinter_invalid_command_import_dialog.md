# Claude Code Prompt: BUG FIX - Tkinter Invalid Command Name Error

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

## Bug Description

Terminal shows this error repeatedly:

```
File "/usr/local/Cellar/python@3.13/3.13.11/Frameworks/Python.framework/Versions/3.13/lib/python3.13/tkinter/__init__.py", line 1812, in _configure
    self.tk.call(_flatten((self._w, cmd)) + self._options(cnf))
_tkinter.TclError: invalid command name ".!importdialog.!ctklabel3.!label"
```

## Root Cause

This error occurs when code tries to configure/update a Tkinter widget after it has been destroyed. The widget path `.!importdialog.!ctklabel3.!label` indicates:
- It's in the ImportDialog
- It's a CTkLabel widget (label #3)
- The dialog was closed/destroyed but something is still trying to update the label

Common causes:
1. **Delayed callback (`after()`)** — A scheduled callback runs after dialog closes
2. **Variable trace** — A StringVar/IntVar trace fires after widget destruction
3. **Thread callback** — Background thread tries to update UI after dialog closes
4. **Progress update** — Import progress callback runs after completion/close

## Investigation Steps

1. Search for `ImportDialog` class in `src/ui/dialogs/`
2. Look for:
   - `self.after()` calls — these need cancellation on dialog close
   - Variable traces (`trace_add`) — these need removal on close
   - Progress callbacks — need to check if dialog still exists
   - Any `configure()` or `config()` calls on labels

3. Check the dialog's close/destroy handling:
   - Is there a `destroy()` override?
   - Are cleanup methods called before destruction?

## Fix Pattern

### Option 1: Cancel scheduled callbacks
```python
def __init__(self):
    self._after_ids = []
    
def schedule_update(self):
    after_id = self.after(100, self.update_something)
    self._after_ids.append(after_id)

def destroy(self):
    for after_id in self._after_ids:
        self.after_cancel(after_id)
    super().destroy()
```

### Option 2: Check widget existence before update
```python
def update_label(self, text):
    if self.winfo_exists():
        self.label.configure(text=text)
```

### Option 3: Remove variable traces on close
```python
def __init__(self):
    self.my_var = ctk.StringVar()
    self._trace_id = self.my_var.trace_add("write", self.on_var_change)

def destroy(self):
    self.my_var.trace_remove("write", self._trace_id)
    super().destroy()
```

## Files to Investigate

- `src/ui/dialogs/import_dialog.py` or similar
- Search for "ImportDialog" class
- Look for `CTkLabel` widgets and what updates them

## Testing

1. Open Import Dialog
2. Perform an import (or cancel)
3. Close dialog
4. Check terminal — no `TclError` should appear
5. Repeat several times to ensure no race conditions

## Deliverables

1. Identify the specific callback/trace causing the error
2. Add proper cleanup on dialog close
3. Error no longer appears in terminal
