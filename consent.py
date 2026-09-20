import tkinter as tk
from tkinter import messagebox


PRIVACY_POLICY = """Privacy Policy

This application uses your camera to detect facial landmarks, eye position, and
optional hand gestures for local cursor control. Camera frames are processed
locally on this computer and are not intentionally recorded, uploaded, or shared
by this application. The application may move your mouse and generate clicks
when those features are enabled.

We recommend that you review the source code of this application to verify that
it does not intentionally record or share your camera feed. You can also run
the application in a sandbox or virtual machine to monitor its behavior. The
application may use third-party libraries for computer vision and machine
learning, which may have their own privacy policies. Please review those
policies if you are concerned about privacy.

We include AI-generated code in this application, which may have been trained on publicly
available data. We do not intentionally include any private or sensitive data in the
training data, and we do not intentionally collect or share any private or sensitive
data from users of this application. However, we cannot guarantee that the AI-generated
code is free from any private or sensitive data, and we encourage users to review the
code and report any concerns to the developers.

We use a AI to act as a assistant to help you when using this application.
We cannot guarantee that the AI will always provide accurate or appropriate responses,
and we encourage users to use their own judgment and discretion when
interacting with the AI. The AI may generate responses based on publicly available data, 
and we do not intentionally include any private or sensitive data in the training data. However, 
we cannot guarantee that the AI-generated responses are free from any private or sensitive data, 
and we encourage users to review the responses and report any concerns to the developers.

You may contact the developers of this application at jonathan.prattipati@gmail.com and rcgafford@gmail.com

You can stop the application at any time by pressing Q or closing the windows.
"""

TERMS = """Terms of Conditions

You use this application at your own risk. The application is experimental and
may move the cursor or click unexpectedly. Do not use it where an accidental
mouse action could cause harm, data loss, or an unintended purchase.

By agreeing, you confirm that you understand the controls and accept
responsibility for using the application on your computer.
"""


def request_consent():
    result = {"accepted": False}
    window = tk.Tk()
    window.title("Eye Tracker - Consent Required")
    window.geometry("720x620")
    window.resizable(False, False)
    window.protocol("WM_DELETE_WINDOW", window.destroy)

    title = tk.Label(
        window,
        text="Consent Required",
        font=("Segoe UI", 18, "bold")
    )
    title.pack(pady=(18, 4))

    subtitle = tk.Label(
        window,
        text="Please review and accept both documents before starting.",
        font=("Segoe UI", 10)
    )
    subtitle.pack(pady=(0, 12))

    documents = tk.Frame(window)
    documents.pack(fill="both", expand=True, padx=18)

    privacy_frame = tk.LabelFrame(
        documents,
        text="Privacy Policy",
        font=("Segoe UI", 10, "bold")
    )
    privacy_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

    privacy_text = tk.Text(
        privacy_frame,
        wrap="word",
        height=18,
        width=38,
        font=("Segoe UI", 9),
        relief="flat",
        padx=8,
        pady=8
    )
    privacy_text.insert("1.0", PRIVACY_POLICY)
    privacy_text.configure(state="disabled")
    privacy_text.pack(fill="both", expand=True)

    terms_frame = tk.LabelFrame(
        documents,
        text="Terms of Conditions",
        font=("Segoe UI", 10, "bold")
    )
    terms_frame.pack(side="right", fill="both", expand=True, padx=(6, 0))

    terms_text = tk.Text(
        terms_frame,
        wrap="word",
        height=18,
        width=38,
        font=("Segoe UI", 9),
        relief="flat",
        padx=8,
        pady=8
    )
    terms_text.insert("1.0", TERMS)
    terms_text.configure(state="disabled")
    terms_text.pack(fill="both", expand=True)

    privacy_accepted = tk.BooleanVar(value=False)
    terms_accepted = tk.BooleanVar(value=False)

    def update_agree_button(*_):
        state = "normal" if privacy_accepted.get() and terms_accepted.get() else "disabled"
        agree_button.configure(state=state)

    checks = tk.Frame(window)
    checks.pack(fill="x", padx=18, pady=(12, 4))

    tk.Checkbutton(
        checks,
        text="I agree to the Privacy Policy",
        variable=privacy_accepted,
        command=update_agree_button,
        anchor="w"
    ).pack(fill="x")
    tk.Checkbutton(
        checks,
        text="I agree to the Terms of Conditions",
        variable=terms_accepted,
        command=update_agree_button,
        anchor="w"
    ).pack(fill="x")

    buttons = tk.Frame(window)
    buttons.pack(pady=(4, 18))

    def accept():
        result["accepted"] = True
        window.destroy()

    def decline():
        messagebox.showinfo(
            "Consent required",
            "The application will close because consent was not provided.",
            parent=window
        )
        window.destroy()

    agree_button = tk.Button(
        buttons,
        text="Agree and Start",
        command=accept,
        state="disabled",
        width=18
    )
    agree_button.pack(side="left", padx=6)
    tk.Button(
        buttons,
        text="Decline and Exit",
        command=decline,
        width=18
    ).pack(side="left", padx=6)

    window.mainloop()
    return result["accepted"]
