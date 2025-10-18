import customtkinter as ctk

class PinPopup(ctk.CTkToplevel):
    def __init__(self, master=None, correct_pin="1234", pin_length=4):
        super().__init__(master)
        self.correct_pin = str(correct_pin)
        self.pin_length = pin_length
        self.result = None
        self.title("Enter PIN")
        self.configure(fg_color="#000000")
        self.geometry("240x400")
        self.resizable(False, False)

        # Entry box (hidden input)
        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, show="*", font=("Segoe UI", 18),
                                   corner_radius=8, fg_color="#1c1c1c", text_color="#ffffff",
                                   placeholder_text="Enter PIN")
        self.entry.pack(pady=(20, 10), padx=20, fill="x")
        self.entry.bind("<Key>", lambda e: "break")  # block typing manually

        # Info label
        self.info_label = ctk.CTkLabel(self, text="Enter PIN", font=("Segoe UI", 12), text_color="#ffffff")
        self.info_label.pack(pady=(0, 10))

        # Buttons frame (vertical grid)
        btn_frame = ctk.CTkFrame(self, fg_color="#000000")
        btn_frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.buttons = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["⌫", "0", "✓"]
        ]

        for r, row in enumerate(self.buttons):
            for c, char in enumerate(row):
                btn = ctk.CTkButton(btn_frame, text=char, font=("Segoe UI", 16),
                                     corner_radius=8, fg_color="#1c1c1c", hover_color="#333333",
                                     text_color="#ffffff",
                                     command=lambda ch=char: self.on_press(ch))
                btn.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        # Make grid cells expand evenly
        for i in range(3):
            btn_frame.grid_columnconfigure(i, weight=1)
        for i in range(4):
            btn_frame.grid_rowconfigure(i, weight=1)

    def on_press(self, char):
        current = self.entry_var.get()
        if char.isdigit():
            if len(current) < self.pin_length:
                self.entry_var.set(current + char)
        elif char == "⌫":
            self.entry_var.set(current[:-1])
        elif char == "✓":
            entered = self.entry_var.get().strip()
            if len(entered) != self.pin_length:
                self.info_label.configure(text=f"❌ Enter {self.pin_length} digits", text_color="#FF5252")
                return
            if entered == self.correct_pin:
                self.info_label.configure(text="✅ PIN Accepted", text_color="#00E676")
                self.result = entered
                self.after(1000, self.destroy)
            else:
                self.info_label.configure(text="❌ PIN Rejected", text_color="#FF5252")
                self.result = False
                self.entry_var.set("")

def launch_pin_popup(parent=None, correct_pin="1234", pin_length=4):
    popup = PinPopup(parent, correct_pin=correct_pin, pin_length=pin_length)
    popup.transient(parent)   # keep popup on top of parent
    popup.grab_set()          # modal - block interaction with other windows
    popup.focus_force()       # force focus (important for touchscreens)
    popup.lift()              # bring popup to front
    return popup




if __name__ == "__main__":
    root = ctk.CTk()
    root.withdraw()  # hide main app for testing
    
    popup = launch_pin_popup(root, correct_pin="1234")

    def check_result():
        if popup.winfo_exists():  # still open
            popup.after(100, check_result)
        else:
            print("Entered PIN:", popup.result)
            root.destroy()

    check_result()
    root.mainloop()


