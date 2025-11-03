"""
Reusable dialog widgets for the Seasonal Baking Tracker.

Provides common dialog types: confirmation, error, success, info.
"""

import customtkinter as ctk
from tkinter import messagebox


def show_confirmation(
    title: str,
    message: str,
    parent=None,
) -> bool:
    """
    Show a confirmation dialog.

    Args:
        title: Dialog title
        message: Confirmation message
        parent: Parent window (optional)

    Returns:
        True if user confirmed, False otherwise
    """
    return messagebox.askyesno(title, message, parent=parent)


def show_error(
    title: str,
    message: str,
    parent=None,
):
    """
    Show an error dialog.

    Args:
        title: Dialog title
        message: Error message
        parent: Parent window (optional)
    """
    messagebox.showerror(title, message, parent=parent)


def show_success(
    title: str,
    message: str,
    parent=None,
):
    """
    Show a success dialog.

    Args:
        title: Dialog title
        message: Success message
        parent: Parent window (optional)
    """
    messagebox.showinfo(title, message, parent=parent)


def show_info(
    title: str,
    message: str,
    parent=None,
):
    """
    Show an information dialog.

    Args:
        title: Dialog title
        message: Information message
        parent: Parent window (optional)
    """
    messagebox.showinfo(title, message, parent=parent)


def show_warning(
    title: str,
    message: str,
    parent=None,
):
    """
    Show a warning dialog.

    Args:
        title: Dialog title
        message: Warning message
        parent: Parent window (optional)
    """
    messagebox.showwarning(title, message, parent=parent)


class CustomInputDialog(ctk.CTkToplevel):
    """
    Custom input dialog for getting user input.

    A simple dialog with an entry field and OK/Cancel buttons.
    """

    def __init__(
        self,
        parent,
        title: str,
        prompt: str,
        default_value: str = "",
    ):
        """
        Initialize the input dialog.

        Args:
            parent: Parent window
            title: Dialog title
            prompt: Prompt text
            default_value: Default input value
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        self.result = None

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Prompt label
        prompt_label = ctk.CTkLabel(self, text=prompt)
        prompt_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Entry field
        self.entry = ctk.CTkEntry(self, width=360)
        self.entry.grid(row=1, column=0, padx=20, pady=10)
        self.entry.insert(0, default_value)
        self.entry.focus()

        # Buttons frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=(10, 20))

        # OK button
        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            width=100,
            command=self._ok_clicked,
        )
        ok_button.grid(row=0, column=0, padx=5)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self._cancel_clicked,
        )
        cancel_button.grid(row=0, column=1, padx=5)

        # Bind Enter key
        self.entry.bind("<Return>", lambda e: self._ok_clicked())

    def _ok_clicked(self):
        """Handle OK button click."""
        self.result = self.entry.get()
        self.destroy()

    def _cancel_clicked(self):
        """Handle Cancel button click."""
        self.result = None
        self.destroy()

    def get_input(self) -> str:
        """
        Get the user input.

        Returns:
            User input string, or None if cancelled
        """
        self.wait_window()
        return self.result
