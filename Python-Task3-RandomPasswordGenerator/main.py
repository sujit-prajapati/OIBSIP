
import tkinter as tk
from tkinter import messagebox
import secrets
import string

# Main application window
root = tk.Tk()
root.title("Secure Password Generator")
root.geometry("600x700")
root.resizable(False, False)
root.configure(bg="#F4F6F9")

# Heading
heading = tk.Label(
    root,
    text="Password Generator",
    font=("Arial", 24, "bold"),
    bg="#F4F6F9",
    fg="#1F2937"
)
heading.pack(pady=(25, 5))

subtitle = tk.Label(
    root,
    text="Create strong and secure passwords",
    font=("Arial", 11),
    bg="#F4F6F9",
    fg="#6B7280"
)
subtitle.pack(pady=5)

# Main frame
main_frame = tk.Frame(root, bg="white", padx=25, pady=20)
main_frame.pack(padx=35, pady=20, fill="both", expand=True)

# Password length
length_label = tk.Label(
    main_frame,
    text="Password Length",
    font=("Arial", 12, "bold"),
    bg="white"
)
length_label.pack(anchor="w", pady=(5, 8))

password_length = tk.IntVar(value=16)

length_input = tk.Spinbox(
    main_frame,
    from_=8,
    to=64,
    textvariable=password_length,
    width=10,
    font=("Arial", 12)
)
length_input.pack(anchor="w", pady=(0, 15))

# Character selection
options_label = tk.Label(
    main_frame,
    text="Select Character Types",
    font=("Arial", 12, "bold"),
    bg="white"
)
options_label.pack(anchor="w", pady=8)

uppercase_var = tk.BooleanVar(value=True)
lowercase_var = tk.BooleanVar(value=True)
numbers_var = tk.BooleanVar(value=True)
symbols_var = tk.BooleanVar(value=True)

options = [
    ("Uppercase Letters (A-Z)", uppercase_var),
    ("Lowercase Letters (a-z)", lowercase_var),
    ("Numbers (0-9)", numbers_var),
    ("Symbols (!@#$)", symbols_var)
]

for text, variable in options:
    checkbox = tk.Checkbutton(
        main_frame,
        text=text,
        variable=variable,
        font=("Arial", 11),
        bg="white",
        activebackground="white"
    )
    checkbox.pack(anchor="w", pady=3)


# Password generation function
def generate_password():

    try:
        length = password_length.get()

        if length < 8 or length > 64:
            messagebox.showerror(
                "Invalid Length",
                "Password length must be between 8 and 64."
            )
            return

    except (tk.TclError, ValueError):
        messagebox.showerror(
            "Invalid Input",
            "Please enter a valid password length."
        )
        return

    character_groups = []

    if uppercase_var.get():
        character_groups.append(string.ascii_uppercase)

    if lowercase_var.get():
        character_groups.append(string.ascii_lowercase)

    if numbers_var.get():
        character_groups.append(string.digits)

    if symbols_var.get():
        character_groups.append("!@#$%^&*()-_=+[]{}?")

    if not character_groups:
        messagebox.showwarning(
            "Select Options",
            "Please select at least two character types."
        )
        return

    if len(character_groups) > length:
        messagebox.showerror(
            "Invalid Length",
            "Password length is too small for selected options."
        )
        return

    # Guarantee one character from each selected group
    password_chars = [
        secrets.choice(group)
        for group in character_groups
    ]

    # Combine all selected character groups
    all_characters = "".join(character_groups)

    # Fill the remaining password length
    for _ in range(length - len(password_chars)):
        password_chars.append(secrets.choice(all_characters))

    # Securely shuffle password characters
    secrets.SystemRandom().shuffle(password_chars)

    # Final password
    password = "".join(password_chars)

    password_var.set(password)


# Password output
output_label = tk.Label(
    main_frame,
    text="Generated Password",
    font=("Arial", 12, "bold"),
    bg="white"
)
output_label.pack(anchor="w", pady=(20, 8))

password_var = tk.StringVar()

password_output = tk.Entry(
    main_frame,
    textvariable=password_var,
    font=("Arial", 12),
    justify="center",
    state="readonly",
    readonlybackground="#F3F4F6",
    width=35
)
password_output.pack(pady=5, ipady=7)

# Generate button
generate_button = tk.Button(
    main_frame,
    text="Generate Password",
    command=generate_password,
    font=("Arial", 12, "bold"),
    bg="#2563EB",
    fg="white",
    activebackground="#1D4ED8",
    activeforeground="white",
    cursor="hand2",
    relief="flat",
    padx=20,
    pady=10
)
generate_button.pack(pady=15)

# Run application
root.mainloop()
