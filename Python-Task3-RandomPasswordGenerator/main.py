import tkinter as tk
from tkinter import messagebox
import secrets
import string
import pyperclip


# ==========================================
# SECURE PASSWORD GENERATOR
# Oasis Infobyte - Python Task 3 (Advanced)
# ==========================================


class PasswordGenerator:

    def __init__(self, root):

        self.root = root
        self.root.title("Secure Password Generator")
        self.root.resizable(False, True)
        self.root.configure(bg="#F4F6F9")

        # Variables
        self.password_length = tk.IntVar(value=16)

        self.uppercase_var = tk.BooleanVar(value=True)
        self.lowercase_var = tk.BooleanVar(value=True)
        self.numbers_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)

        self.exclude_ambiguous_var = tk.BooleanVar(value=False)

        self.password_var = tk.StringVar()

        # Password history
        self.password_history = []

        # Build GUI
        self.create_widgets()

        # Window ko content ke size ke hisaab se set karo
        self.fit_window_to_screen()

        # X button dabane par history clear karke band karo
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ======================================
    # GUI DESIGN
    # ======================================

    def create_widgets(self):

        # Heading
        heading = tk.Label(
            self.root,
            text="Password Generator",
            font=("Arial", 22, "bold"),
            bg="#F4F6F9",
            fg="#1F2937"
        )
        heading.pack(pady=(14, 0))

        subtitle = tk.Label(
            self.root,
            text="Create strong and secure passwords",
            font=("Arial", 11),
            bg="#F4F6F9",
            fg="#6B7280"
        )
        subtitle.pack(pady=(2, 8))

        # Main frame
        main_frame = tk.Frame(
            self.root,
            bg="white",
            padx=25,
            pady=12
        )
        main_frame.pack(
            padx=35,
            pady=(0, 15),
            fill="both",
            expand=True
        )

        # Password length (label aur spinbox ek hi row mein)
        length_row = tk.Frame(main_frame, bg="white")
        length_row.pack(fill="x", pady=(2, 8))

        tk.Label(
            length_row,
            text="Password Length",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(side="left")

        self.length_input = tk.Spinbox(
            length_row,
            from_=8,
            to=64,
            textvariable=self.password_length,
            width=8,
            font=("Arial", 12)
        )
        self.length_input.pack(side="left", padx=(15, 0))

        # Character options (2 x 2 grid)
        tk.Label(
            main_frame,
            text="Select Character Types",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(4, 4))

        options_frame = tk.Frame(main_frame, bg="white")
        options_frame.pack(fill="x")

        options = [
            ("Uppercase Letters (A-Z)", self.uppercase_var),
            ("Lowercase Letters (a-z)", self.lowercase_var),
            ("Numbers (0-9)", self.numbers_var),
            ("Symbols (!@#$)", self.symbols_var)
        ]

        for index, (text, variable) in enumerate(options):

            tk.Checkbutton(
                options_frame,
                text=text,
                variable=variable,
                font=("Arial", 10),
                bg="white",
                activebackground="white"
            ).grid(
                row=index // 2,
                column=index % 2,
                sticky="w",
                padx=(0, 25),
                pady=2
            )

        # Exclude ambiguous characters
        tk.Checkbutton(
            main_frame,
            text="Exclude ambiguous characters (0, O, 1, l, I)",
            variable=self.exclude_ambiguous_var,
            font=("Arial", 10),
            bg="white",
            activebackground="white"
        ).pack(anchor="w", pady=(6, 8))

        # Generated password label
        tk.Label(
            main_frame,
            text="Generated Password",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(anchor="w", pady=(4, 3))

        self.password_output = tk.Entry(
            main_frame,
            textvariable=self.password_var,
            font=("Arial", 12),
            justify="center",
            state="readonly",
            readonlybackground="#F3F4F6",
            width=42
        )
        self.password_output.pack(pady=3, ipady=6)

        # Strength indicator
        self.strength_label = tk.Label(
            main_frame,
            text="Password Strength: Not Generated",
            font=("Arial", 11, "bold"),
            bg="white",
            fg="gray"
        )
        self.strength_label.pack(pady=(6, 6))

        # Buttons (side by side, taaki neeche history ke liye jagah bache)
        button_frame = tk.Frame(main_frame, bg="white")
        button_frame.pack(pady=(2, 4))

        tk.Button(
            button_frame,
            text="Generate Password",
            command=self.generate_password,
            font=("Arial", 11, "bold"),
            bg="#2563EB",
            fg="white",
            activebackground="#1D4ED8",
            activeforeground="white",
            cursor="hand2",
            relief="flat",
            padx=18,
            pady=8
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="Copy Password",
            command=self.copy_password,
            font=("Arial", 11, "bold"),
            bg="#16A34A",
            fg="white",
            activebackground="#15803D",
            activeforeground="white",
            cursor="hand2",
            relief="flat",
            padx=18,
            pady=8
        ).pack(side="left", padx=8)

        # Password history (label + Clear History button ek row mein)
        history_header = tk.Frame(main_frame, bg="white")
        history_header.pack(fill="x", pady=(8, 3))

        tk.Label(
            history_header,
            text="Recent Password History",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(side="left")

        tk.Button(
            history_header,
            text="Clear History",
            command=self.clear_history,
            font=("Arial", 9, "bold"),
            bg="#DC2626",
            fg="white",
            activebackground="#B91C1C",
            activeforeground="white",
            cursor="hand2",
            relief="flat",
            padx=12,
            pady=3
        ).pack(side="right")

        self.history_list = tk.Listbox(
            main_frame,
            height=5,
            font=("Consolas", 10),
            width=55,
            bg="#F9FAFB",
            selectbackground="#2563EB"
        )
        self.history_list.pack(fill="x", pady=3)

        # Select history item to display
        self.history_list.bind(
            "<<ListboxSelect>>",
            self.select_history
        )

        # Footer
        tk.Label(
            main_frame,
            text="History is kept in memory only and cleared when the app closes",
            font=("Arial", 9),
            bg="white",
            fg="#9CA3AF"
        ).pack(pady=(4, 0))

    # ======================================
    # WINDOW SIZE
    # ======================================

    def fit_window_to_screen(self):

        # Tkinter se content ka asli size poochho
        self.root.update_idletasks()

        width = max(self.root.winfo_reqwidth(), 650)
        height = self.root.winfo_reqheight()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Taskbar ke liye thodi jagah chhodo
        height = min(height, screen_height - 100)

        # Window ko screen ke beech mein rakho
        x = (screen_width - width) // 2
        y = max((screen_height - height) // 2 - 20, 0)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, min(height, 480))

    # ======================================
    # CHARACTER GROUPS
    # ======================================

    def get_character_groups(self):

        groups = []

        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        numbers = string.digits
        symbols = "!@#$%^&*()-_=+[]{}?"

        if self.exclude_ambiguous_var.get():

            ambiguous = "0O1lI"

            uppercase = "".join(
                char for char in uppercase
                if char not in ambiguous
            )

            lowercase = "".join(
                char for char in lowercase
                if char not in ambiguous
            )

            numbers = "".join(
                char for char in numbers
                if char not in ambiguous
            )

        if self.uppercase_var.get():
            groups.append(uppercase)

        if self.lowercase_var.get():
            groups.append(lowercase)

        if self.numbers_var.get():
            groups.append(numbers)

        if self.symbols_var.get():
            groups.append(symbols)

        return groups

    # ======================================
    # PASSWORD GENERATION
    # ======================================

    def generate_password(self):

        try:
            length = int(self.length_input.get().strip())

        except ValueError:

            messagebox.showerror(
                "Invalid Input",
                "Please enter a valid password length."
            )
            return

        if not 8 <= length <= 64:

            messagebox.showerror(
                "Invalid Length",
                "Password length must be between 8 and 64."
            )
            return

        groups = self.get_character_groups()

        if len(groups) < 2:

            messagebox.showwarning(
                "Select Options",
                "Please select at least 2 character types."
            )
            return

        if len(groups) > length:

            messagebox.showerror(
                "Invalid Length",
                "Password length is too small for selected options."
            )
            return

        # Select at least one character from each group
        password_characters = [
            secrets.choice(group)
            for group in groups
        ]

        # Combine all selected character groups
        all_characters = "".join(groups)

        # Fill remaining password length
        for _ in range(length - len(password_characters)):

            password_characters.append(
                secrets.choice(all_characters)
            )

        # Securely shuffle characters
        secrets.SystemRandom().shuffle(password_characters)

        # Create final password
        password = "".join(password_characters)

        # Display password
        self.password_var.set(password)

        # Update strength
        self.update_strength(password)

        # Save password history
        self.add_to_history(password)

    # ======================================
    # PASSWORD STRENGTH
    # ======================================

    def calculate_strength(self, password):

        categories = 0

        if any(char.isupper() for char in password):
            categories += 1

        if any(char.islower() for char in password):
            categories += 1

        if any(char.isdigit() for char in password):
            categories += 1

        if any(not char.isalnum() for char in password):
            categories += 1

        # Basic estimate from length and character diversity only.
        # This is a general guide, not a formal security / entropy assessment.
        if len(password) >= 16 and categories >= 3:

            return "Strong"

        elif len(password) >= 12 and categories >= 2:

            return "Medium"

        else:

            return "Weak"

    def update_strength(self, password):

        strength = self.calculate_strength(password)

        if strength == "Strong":

            color = "#16A34A"

        elif strength == "Medium":

            color = "#D97706"

        else:

            color = "#DC2626"

        self.strength_label.config(
            text=f"Password Strength: {strength}",
            fg=color
        )

    # ======================================
    # COPY PASSWORD
    # ======================================

    def copy_password(self):

        password = self.password_var.get()

        if not password:

            messagebox.showwarning(
                "No Password",
                "Please generate a password first."
            )
            return

        try:

            pyperclip.copy(password)

            messagebox.showinfo(
                "Copied",
                "Password copied to clipboard successfully!"
            )

        except pyperclip.PyperclipException as error:

            messagebox.showerror(
                "Copy Error",
                f"Unable to copy password: {error}"
            )

    # ======================================
    # PASSWORD HISTORY
    # ======================================

    def add_to_history(self, password):

        self.password_history.insert(0, password)

        # Keep only last five passwords
        self.password_history = self.password_history[:5]

        self.history_list.delete(0, tk.END)

        for item in self.password_history:

            self.history_list.insert(tk.END, item)

    def select_history(self, event):

        selection = self.history_list.curselection()

        if selection:

            index = selection[0]

            password = self.password_history[index]

            self.password_var.set(password)

            self.update_strength(password)

    def clear_history(self):

        if not self.password_history:

            messagebox.showinfo(
                "History Empty",
                "There is no password history to clear."
            )
            return

        self.password_history.clear()
        self.history_list.delete(0, tk.END)

        messagebox.showinfo(
            "History Cleared",
            "Password history has been cleared."
        )

    # ======================================
    # APPLICATION CLOSE
    # ======================================

    def on_close(self):

        # History sirf memory mein hai; band karne se pehle clear karo
        self.password_history.clear()
        self.history_list.delete(0, tk.END)
        self.password_var.set("")

        self.root.destroy()


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    root = tk.Tk()

    app = PasswordGenerator(root)

    root.mainloop()