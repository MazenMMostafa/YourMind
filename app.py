
import tkinter as tk
from tkinter import messagebox
import threading
import datetime
import time

class MedicationReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("منبه الدواء")
        self.root.geometry("300x250")

        tk.Label(root, text="اختر وقت الدواء:", font=("Arial", 12)).pack(pady=10)

        self.hour_var = tk.StringVar(root)
        self.minute_var = tk.StringVar(root)
        self.hour_var.set("0")
        self.minute_var.set("0")

        # قائمة اختيار الساعة والدقائق
        hour_menu = tk.OptionMenu(root, self.hour_var, *[str(i) for i in range(24)])
        minute_menu = tk.OptionMenu(root, self.minute_var, *[str(i) for i in range(60)])
        hour_menu.pack(pady=5)
        minute_menu.pack(pady=5)

        # زر حفظ الموعد
        save_button = tk.Button(root, text="حفظ الموعد", command=self.set_medication_time)
        save_button.pack(pady=10)

    def set_medication_time(self):
        hour = int(self.hour_var.get())
        minute = int(self.minute_var.get())

        now = datetime.datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if target_time < now:
            target_time += datetime.timedelta(days=1)

        delay = (target_time - now).total_seconds()

        # تشغيل المنبه في الوقت المحدد باستخدام threading
        threading.Thread(target=self.wait_and_notify, args=(delay,), daemon=True).start()

        messagebox.showinfo("تم الحفظ", f"تم ضبط المنبه على {hour:02}:{minute:02}")

    def wait_and_notify(self, delay):
        time.sleep(delay)
        messagebox.showinfo("🔔 تنبيه", "حان وقت تناول الدواء!")

if __name__ == "__main__":
    root = tk.Tk()
    app = MedicationReminderApp(root)
    root.mainloop()
