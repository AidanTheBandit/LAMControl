import tkinter as tk
from tkinter import ttk, messagebox
from . import config

def create_env_file():
    """Creates a .env file with user-provided credentials."""
    try:
        credentials = {}
        
        # Always include GROQ API Key
        credentials["GROQ_API_KEY"] = groq_api_key_entry.get()
        
        # Include other credentials based on mode and if fields exist
        current_mode = config.config.get("mode", "rabbit")
        
        if current_mode in ["rabbit", "cli"]:
            # Rabbit mode requires the access token
            credentials["RH_ACCESS_TOKEN"] = rh_access_token_entry.get()
        
        # Always include optional integration credentials if provided
        if 'dc_email_entry' in globals() and dc_email_entry.get():
            credentials["DC_EMAIL"] = dc_email_entry.get()
        if 'dc_pass_entry' in globals() and dc_pass_entry.get():
            credentials["DC_PASS"] = dc_pass_entry.get()
        if 'fb_email_entry' in globals() and fb_email_entry.get():
            credentials["FB_EMAIL"] = fb_email_entry.get()
        if 'fb_pass_entry' in globals() and fb_pass_entry.get():
            credentials["FB_PASS"] = fb_pass_entry.get()
        if 'gh_email_entry' in globals() and gh_email_entry.get():
            credentials["G_HOME_EMAIL"] = gh_email_entry.get()
        if 'gh_pass_entry' in globals() and gh_pass_entry.get():
            credentials["G_HOME_PASS"] = gh_pass_entry.get()

        with open(".env", "w") as env_file:
            for key, value in credentials.items():
                env_file.write(f"{key}='{value}'\n")
        messagebox.showinfo("Success", ".env file created successfully!")
        root.destroy()  # Close the UI window
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def create_ui():
    """Creates and runs the UI for credential input."""
    global root, rh_access_token_entry, fb_email_entry, fb_pass_entry, dc_email_entry, dc_pass_entry, groq_api_key_entry, gh_email_entry, gh_pass_entry
    
    current_mode = config.config.get("mode", "rabbit")
    
    root = tk.Tk()
    root.title(f"LAMControl - Enter Credentials ({current_mode.upper()} mode)")
    root.configure(bg='#1a1a1a')

    # Set window size and prevent fullscreen
    root.geometry("600x500")
    root.resizable(False, False)  # Disable resizing

    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TLabel', background='#1a1a1a', foreground='#ff6600')
    style.configure('TEntry', fieldbackground='#333333', foreground='#ffffff')
    style.configure('TButton', background='#ff6600', foreground='#ffffff')

    # Create a frame to hold the input fields and labels
    input_frame = tk.Frame(root, bg='#1a1a1a')
    input_frame.pack(expand=True, fill='both', padx=20, pady=20)

    # Mode info label
    mode_info = ttk.Label(input_frame, text=f"Current mode: {current_mode.upper()}", font=('Arial', 12, 'bold'))
    mode_info.grid(row=0, column=0, columnspan=2, padx=5, pady=(0, 10), sticky='w')
    
    if current_mode == "web":
        info_text = "Web mode: Only GROQ API Key is required. Other credentials are optional for integrations."
    elif current_mode == "rabbit":
        info_text = "Rabbit mode: Rabbit Hole Access Token and GROQ API Key are required."
    else:
        info_text = "CLI mode: Rabbit Hole Access Token and GROQ API Key are required."
    
    info_label = ttk.Label(input_frame, text=info_text, wraplength=550)
    info_label.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 15), sticky='w')

    # Define the fields based on mode
    fields = []
    current_row = 2
    
    # Always show GROQ API Key (required for all modes)
    fields.append(("GROQ API Key (Required):", "groq_api_key_entry", True, True))
    
    # Show Rabbit Hole token only for rabbit/cli modes
    if current_mode in ["rabbit", "cli"]:
        fields.append(("Rabbit Hole Access Token (Required):", "rh_access_token_entry", True, True))
    
    # Optional integration fields (always show but mark as optional)
    fields.extend([
        ("Discord Email (Optional):", "dc_email_entry", False, False),
        ("Discord Password (Optional):", "dc_pass_entry", True, False),
        ("Facebook Email (Optional):", "fb_email_entry", False, False),
        ("Facebook Password (Optional):", "fb_pass_entry", True, False),
        ("Google Home Email (Optional):", "gh_email_entry", False, False),
        ("Google Home Password (Optional):", "gh_pass_entry", True, False)
    ])

    # Create and place the labels and entries dynamically
    for i, (label_text, var_name, is_password, is_required) in enumerate(fields):
        row_num = current_row + i
        label = ttk.Label(input_frame, text=label_text)
        label.grid(row=row_num, column=0, padx=5, pady=5, sticky='w')
        
        entry = ttk.Entry(input_frame, show="*" if is_password else "")
        entry.grid(row=row_num, column=1, padx=5, pady=5, sticky='ew')
        globals()[var_name] = entry
        
        # Add visual indicator for required fields
        if is_required:
            entry.configure(style="Required.TEntry")

    # Custom style for required fields
    style.configure("Required.TEntry", fieldbackground='#443333', foreground='#ffffff')

    # Submit Button
    submit_button = ttk.Button(root, text="Submit", command=create_env_file)
    submit_button.pack(pady=15)

    # Make input fields expand to fill the width
    for i in range(len(fields) + 2):  # +2 for mode info and description
        input_frame.grid_rowconfigure(i, weight=1)
    input_frame.grid_columnconfigure(1, weight=1)

    root.mainloop()  # Run the UI