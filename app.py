import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

import pipeline


class App:
    def __init__(self, root):
        self.root = root
        root.title("Synthesis")
        root.geometry("900x650")

        top = tk.Frame(root)
        top.pack(fill="x", padx=10, pady=10)
        self.entry = tk.Entry(top, font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.start())
        self.button = tk.Button(top, text="Ask", width=10, command=self.start)
        self.button.pack(side="left", padx=(8, 0))

        self.output = scrolledtext.ScrolledText(root, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.output.configure(state="disabled")

        self.messages = queue.Queue()
        self.root.after(100, self.poll)

    def write(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def start(self):
        question = self.entry.get().strip()
        if not question:
            return
        self.button.configure(state="disabled")
        self.clear()
        self.write(f"Question: {question}\n")
        threading.Thread(target=self.work, args=(question,), daemon=True).start()

    def work(self, question):
        try:
            out = pipeline.run(question, log=self.messages.put)
            if out["ok"]:
                self.messages.put("\n" + out["report"])
            else:
                self.messages.put("\nNo report: " + (out["note"] or "it failed the citation check."))
        except Exception as e:
            self.messages.put(f"\nERROR: {e}")
        self.messages.put(None)  # signals "finished"

    def poll(self):
        while not self.messages.empty():
            msg = self.messages.get()
            if msg is None:
                self.button.configure(state="normal")
            else:
                self.write(msg)
        self.root.after(100, self.poll)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()