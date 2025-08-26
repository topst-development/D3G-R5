import os
import logging
import queue
from datetime import datetime
import re
import threading
import time
import tkinter as tk
from tkinter import ttk
 
import serial
import serial.tools.list_ports
 
class CANMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
 
        self.title("TOPST-D3 CAN Viewer v1.0")
        # self.geometry("1080x1000")  # 창 크기를 조금 더 크게 설정
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.can_id_count = {}      # CAN ID count dictionary
        self.thrs_queue_dict = {}   # Thread's queue dictionary
        self.data_queue = queue.Queue(maxsize=5000)  # Queue for thread communication
        self.log_queue = queue.Queue(maxsize=5000)  # Queue for thread communication
        
        self.stop_update_view = False

        self.clicked_send_btn = False
        self.clicked_send_repeat_btn = False
        self.clicked_send_stop_btn = False
        
         # Create log folder and file
        log_folder = "log"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        log_filename = os.path.join(log_folder, f"can_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        # Configure logging
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_filename, delay=False)
        self.logger.addHandler(handler)
 
        # Top Frame
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
 
        # Group Box
        serial_settings_frame = tk.LabelFrame(top_frame, text="Serial Settings", padx=3, pady=0)
        serial_settings_frame.grid(row=0, column=0, columnspan=3, padx=8, pady=5, sticky="ew")

        # Configure grid weights
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)
        top_frame.grid_columnconfigure(2, weight=1)
        top_frame.grid_columnconfigure(3, weight=1)
        top_frame.grid_columnconfigure(4, weight=1)
        top_frame.grid_columnconfigure(5, weight=1)
        top_frame.grid_columnconfigure(6, weight=1)
        top_frame.grid_columnconfigure(7, weight=1)
        top_frame.grid_columnconfigure(8, weight=1)
        serial_settings_frame.grid_columnconfigure(0, weight=1)
        serial_settings_frame.grid_columnconfigure(1, weight=1)
        serial_settings_frame.grid_columnconfigure(2, weight=1)
        serial_settings_frame.grid_columnconfigure(3, weight=1)

        tk.Label(serial_settings_frame, text="COM Port:").grid(row=0, column=0, padx=(0, 0), pady=5, sticky="w")
        self.com_port = ttk.Combobox(serial_settings_frame, values=[port.device for port in serial.tools.list_ports.comports()], state="readonly", width=7)
        if self.com_port['values']:
            self.com_port.current(0)
        self.com_port.grid(row=0, column=0, padx=(70, 0), pady=5, sticky="w")

        tk.Label(serial_settings_frame, text="Stop Bit:").grid(row=1, column=0, padx=(0, 0), pady=5, sticky="w")
        self.stop_bit = ttk.Combobox(serial_settings_frame, values=["1", "1.5", "2"], state="disabled", width=7)
        self.stop_bit.current(0)
        self.stop_bit.grid(row=1, column=0, padx=(70, 0), pady=5, sticky="w")

        tk.Label(serial_settings_frame, text="Baud Rate:").grid(row=0, column=1, padx=(0, 0), pady=5, sticky="w")
        self.baud_rate = ttk.Combobox(serial_settings_frame, values=["9600", "19200", "38400", "57600", "115200"], state="disabled", width=7)
        self.baud_rate.current(4)
        self.baud_rate.grid(row=0, column=1, padx=(70, 0), pady=5, sticky="w")

        tk.Label(serial_settings_frame, text="Parity Bit:").grid(row=1, column=1, padx=(0, 0), pady=5, sticky="w")
        self.parity_bit = ttk.Combobox(serial_settings_frame, values=["None", "Even", "Odd", "Mark", "Space"], state="disabled", width=7)
        self.parity_bit.current(0)
        self.parity_bit.grid(row=1, column=1, padx=(70, 0), pady=5, sticky="w")

        tk.Label(serial_settings_frame, text="Data Bit:").grid(row=0, column=2, padx=(0, 0), pady=5, sticky="w")
        self.data_bit = ttk.Combobox(serial_settings_frame, values=["5", "6", "7", "8"], state="disabled", width=7)
        self.data_bit.current(3)
        self.data_bit.grid(row=0, column=2, padx=(60, 0), pady=5, sticky="w")

        # Progress Bar
        self.progress = ttk.Progressbar(serial_settings_frame, orient="horizontal", length=100, mode="determinate")
        self.progress.grid(row=1, column=2, columnspan=2, padx=(5, 0), pady=5, sticky="w")

        # OFF Label
        self.status_label = tk.Label(serial_settings_frame, text="OFF", font=("Helvetica", 10, "bold"))
        self.status_label.grid(row=1, column=2, padx=(105, 0), pady=5, sticky="w")

        self.connect_button = tk.Button(serial_settings_frame, text="Connect", width=9, command=self.connect_serial)
        self.connect_button.grid(row=0, column=3, padx=0, pady=5, sticky="w")

        self.disconnect_button = tk.Button(serial_settings_frame, text="Disconnect", width=9, command=self.disconnect_serial)
        self.disconnect_button.grid(row=1, column=3, padx=0, pady=5, sticky="w")
        self.disconnect_button.config(state=tk.DISABLED)

        # CAN Settings Group Box
        can_settings_frame = tk.LabelFrame(top_frame, text="CAN Settings", padx=3, pady=3)
        can_settings_frame.grid(row=0, column=3, columnspan=6, padx=0, pady=5, sticky="ew")

        # Configure grid weights
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)
        top_frame.grid_columnconfigure(2, weight=1)
        top_frame.grid_columnconfigure(3, weight=1)
        top_frame.grid_columnconfigure(4, weight=1)
        top_frame.grid_columnconfigure(5, weight=1)
        top_frame.grid_columnconfigure(6, weight=1)
        top_frame.grid_columnconfigure(7, weight=1)
        top_frame.grid_columnconfigure(8, weight=1)
        serial_settings_frame.grid_columnconfigure(0, weight=1)
        serial_settings_frame.grid_columnconfigure(1, weight=1)
        serial_settings_frame.grid_columnconfigure(2, weight=1)
        serial_settings_frame.grid_columnconfigure(3, weight=1)
        can_settings_frame.grid_columnconfigure(0, weight=1)
        can_settings_frame.grid_columnconfigure(1, weight=1)
        can_settings_frame.grid_columnconfigure(2, weight=1)
        can_settings_frame.grid_columnconfigure(3, weight=1)

        tk.Label(can_settings_frame, text="Channel:").grid(row=0, column=0, padx=(0, 0), pady=5, sticky="w")
        self.channel_var_a = tk.BooleanVar()
        self.channel_var_b = tk.BooleanVar()
        self.channel_var_c = tk.BooleanVar()
        
        self.channel_checkbutton_a = tk.Checkbutton(can_settings_frame, text="A", variable=self.channel_var_a, command=self.update_channel_info)
        self.channel_checkbutton_a.grid(row=0, column=0, padx=(55, 0), pady=5, sticky="w")
        self.channel_var_a.set(True)
        
        self.channel_checkbutton_b = tk.Checkbutton(can_settings_frame, text="B", variable=self.channel_var_b, command=self.update_channel_info)
        self.channel_checkbutton_b.grid(row=0, column=0, padx=(90, 0), pady=5, sticky="w")
        self.channel_var_b.set(True)
        
        self.channel_checkbutton_c = tk.Checkbutton(can_settings_frame, text="C", variable=self.channel_var_c, command=self.update_channel_info)
        self.channel_checkbutton_c.grid(row=0, column=0, padx=(125, 0), pady=5, sticky="w")
        self.channel_var_c.set(True)

        tk.Label(can_settings_frame, text="Bit Rate:").grid(row=1, column=0, padx=(0, 0), pady=5, sticky="w")
        self.nominal_baud_rate = ttk.Combobox(can_settings_frame, values=["100", "200", "250", "500"], width=10, state="readonly")
        self.nominal_baud_rate.current(3)
        self.nominal_baud_rate.grid(row=1, column=0, padx=(60, 0), pady=5, sticky="w")
        self.nominal_baud_rate.bind("<<ComboboxSelected>>", self.update_baud_rate)
        tk.Label(can_settings_frame, text="kbps").grid(row=1, column=0, padx=(160, 0), pady=5, sticky="w")

        tk.Label(can_settings_frame, text="ID Mask:").grid(row=0, column=1, padx=0, pady=5, sticky="e")
        self.id_mask_entries = []
        id_mask_frame = tk.Frame(can_settings_frame)
        id_mask_frame.grid(row=0, column=2, padx=0, pady=5, sticky="w")
        for i in range(11):
            entry = tk.Entry(id_mask_frame, width=1)
            entry.pack(side=tk.LEFT, padx=(0 if i == 0 else 0, 0))
            entry.config(validate="key", validatecommand=(self.register(self.validate_id_mask_entry), "%P"))
            self.id_mask_entries.append(entry)

        # default value
        self.id_mask_entries[0].insert(0, "0")
        self.id_mask_entries[1].insert(0, "0")
        self.id_mask_entries[2].insert(0, "0")
        self.id_mask_entries[3].insert(0, "0")
        self.id_mask_entries[4].insert(0, "0")
        self.id_mask_entries[5].insert(0, "0")
        self.id_mask_entries[6].insert(0, "0")
        self.id_mask_entries[7].insert(0, "0")
        self.id_mask_entries[8].insert(0, "0")
        self.id_mask_entries[9].insert(0, "0")
        self.id_mask_entries[10].insert(0, "0")

        tk.Label(can_settings_frame, text="ID Acceptance:").grid(row=1, column=1, padx=0, pady=5, sticky="e")
        self.id_acceptance_entries = []
        id_acceptance_frame = tk.Frame(can_settings_frame)
        id_acceptance_frame.grid(row=1, column=2, padx=0, pady=5, sticky="w")
        for i in range(11):
            entry = tk.Entry(id_acceptance_frame, width=1)
            entry.pack(side=tk.LEFT, padx=(0 if i == 0 else 0, 0))
            entry.config(validate="key", validatecommand=(self.register(self.validate_id_mask_entry), "%P"))
            self.id_acceptance_entries.append(entry)

        # default value
        self.id_acceptance_entries[0].insert(0, "1")
        self.id_acceptance_entries[1].insert(0, "1")
        self.id_acceptance_entries[2].insert(0, "1")
        self.id_acceptance_entries[3].insert(0, "1")
        self.id_acceptance_entries[4].insert(0, "1")
        self.id_acceptance_entries[5].insert(0, "1")
        self.id_acceptance_entries[6].insert(0, "1")
        self.id_acceptance_entries[7].insert(0, "1")
        self.id_acceptance_entries[8].insert(0, "1")
        self.id_acceptance_entries[9].insert(0, "1")
        self.id_acceptance_entries[10].insert(0, "1")

        # Set Button for both ID Mask and ID Acceptance
        self.set_button = tk.Button(can_settings_frame, text="Set", command=self.set_can_info)
        self.set_button.grid(row=0, column=3, rowspan=2, padx=0, pady=5, sticky="ns")
        self.set_button.config(state=tk.DISABLED)
 
        # Table
        table_frame = tk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
 
        columns = ("timestamp", "channel", "can_id", "Length", "Data", "Count")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("channel", text="Channel")
        self.tree.heading("can_id", text="CAN ID")
        self.tree.heading("Length", text="Length")
        self.tree.heading("Data", text="Data")
        self.tree.heading("Count", text="Count")
 
        # Set column widths
        self.tree.column("timestamp", width=140)
        self.tree.column("channel", width=90)
        self.tree.column("can_id", width=90)
        self.tree.column("Length", width=90)
        self.tree.column("Data", width=490)
        self.tree.column("Count", width=90)
 
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
 
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
 
        # Right-click menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="HEX", command=self.show_hex)
        self.menu.add_command(label="ASCII", command=self.show_ascii)
        self.menu.add_command(label="Clear", command=self.clear_table)
 
        self.tree.bind("<Button-3>", self.show_context_menu)
 
        # Bottom Frame
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=3, pady=5)  # fill=tk.X로 수정

        # Serial Communication Group Box
        serial_comm_frame = tk.LabelFrame(bottom_frame, text="Log", padx=5, pady=5)
        serial_comm_frame.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")

        # Configure grid weights
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)
        bottom_frame.grid_rowconfigure(0, weight=1)
        serial_comm_frame.grid_columnconfigure(0, weight=1)
        serial_comm_frame.grid_rowconfigure(0, weight=1)
        serial_comm_frame.grid_rowconfigure(1, weight=0)

        # 메시지 박스와 스크롤바를 포함하는 프레임
        message_frame = tk.Frame(serial_comm_frame)
        message_frame.grid(row=0, column=0, sticky="nsew")

        self.message_box = tk.Text(message_frame, height=10, width=20)  # height와 width를 줄임
        self.message_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 스크롤바 추가
        self.scrollbar = tk.Scrollbar(message_frame, command=self.message_box.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_box.config(yscrollcommand=self.scrollbar.set)

        send_frame = tk.Frame(serial_comm_frame)
        send_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.clear_button = tk.Button(send_frame, text="Clear", command=self.clear_serial_send_text, width=10)
        self.clear_button.pack(side=tk.RIGHT, padx=0, pady=5, anchor="w")

        self.send_button = tk.Button(send_frame, text="Send", command=self.send_serial_data, width=10)
        self.send_button.pack(side=tk.RIGHT, padx=10, pady=5, anchor="w")
        self.send_button.config(state=tk.DISABLED)

        self.serial_send_text = tk.Entry(send_frame)
        self.serial_send_text.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=0, pady=5, anchor="w")

        self.serial_send_label = tk.Label(send_frame, text="Serial Message", width=15)  # width를 줄임
        self.serial_send_label.pack(side=tk.LEFT, padx=0, pady=5, anchor="w")

        # Sending CAN Message Group Box
        sending_can_frame = tk.LabelFrame(bottom_frame, text="Sending CAN Message", padx=5, pady=5)
        sending_can_frame.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")

        # Configure grid weights
        sending_can_frame.grid_columnconfigure(0, weight=1)
        sending_can_frame.grid_rowconfigure(0, weight=1)
        sending_can_frame.grid_rowconfigure(1, weight=1)
        sending_can_frame.grid_rowconfigure(2, weight=1)
        sending_can_frame.grid_rowconfigure(3, weight=1)
        sending_can_frame.grid_rowconfigure(4, weight=1)

        # CAN ID Label and Entry
        can_id_frame = tk.Frame(sending_can_frame)
        can_id_frame.grid(row=0, column=0, padx=0, pady=5, sticky="ew")
        tk.Label(can_id_frame, text="CAN ID").pack(side=tk.LEFT, padx=10, pady=5)
        self.can_id_label_entry = tk.Entry(can_id_frame, width=24)
        self.can_id_label_entry.pack(side=tk.LEFT, padx=55, pady=5)
        self.can_id_label_entry.config(validate="key", validatecommand=(self.register(self.validate_hex), "%P"))
        # default value
        self.can_id_label_entry.insert(0, "000")

        # CAN Message Label and Entry
        can_message_frame = tk.Frame(sending_can_frame)
        can_message_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        tk.Label(can_message_frame, text="CAN Message").pack(side=tk.LEFT, padx=5, pady=5)
        self.can_message_entry = tk.Entry(can_message_frame, width=24, state=tk.DISABLED)  # 초기 상태를 비활성화로 설정
        self.can_message_entry.pack(side=tk.LEFT, padx=27, pady=5)  # side=tk.LEFT로 수정하여 수평 방향으로 배치
        self.can_message_entry.config(validate="key", validatecommand=(self.register(self.validate_can_id_length), "%P"))

        # ASCII Checkbutton
        self.ascii_var = tk.BooleanVar()
        self.ascii_checkbutton = tk.Checkbutton(can_message_frame, text="ASCII", variable=self.ascii_var, command=self.toggle_ascii)
        self.ascii_checkbutton.pack(side=tk.LEFT, padx=0, pady=5)  # padx 값을 (0, 5)로 설정하여 Entry 쪽으로 붙임

        # DLC Label and Entry
        dlc_frame = tk.Frame(sending_can_frame)
        dlc_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        # Spacer Frame to add distance
        spacer_frame = tk.Frame(dlc_frame, width=115)
        spacer_frame.pack(side=tk.LEFT)

        # 8개의 Entry 생성
        self.dlc_entries = []
        for i in range(8):
            entry = tk.Entry(dlc_frame, width=2)
            entry.insert(0, "00")  # 기본값 설정
            entry.pack(side=tk.LEFT, padx=2, pady=5)
            entry.config(validate="key", validatecommand=(self.register(self.validate_and_move_focus), "%P", i))
            self.dlc_entries.append(entry)

        # HEX Checkbutton
        self.hex_var = tk.BooleanVar(value=True)
        self.hex_checkbutton = tk.Checkbutton(dlc_frame, text="HEX", variable=self.hex_var, command=self.toggle_hex)
        self.hex_checkbutton.pack(side=tk.LEFT, padx=26, pady=5)  # padx 값을 5로 줄임

        tk.Label(dlc_frame, text="DLC").pack(side=tk.LEFT, padx=0, pady=5)  # padx 값을 5로 줄임
        self.dlc_entry = ttk.Combobox(dlc_frame, values=[str(i) for i in range(1, 9)], width=3, state="readonly")
        self.dlc_entry.current(0)  # 기본값 설정
        self.dlc_entry.pack(side=tk.LEFT, padx=0, pady=5)
        self.dlc_entry.bind("<<ComboboxSelected>>", self.update_dlc_entries)

        self.toggle_hex()

        # Send Buttons and Entry
        send_buttons_frame = tk.Frame(sending_can_frame)
        send_buttons_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        self.can_send_repeat_label = tk.Label(send_buttons_frame, text="ms")
        self.can_send_repeat_label.pack(side=tk.RIGHT, padx=0, pady=5)
        self.can_send_repeat_entry = tk.Entry(send_buttons_frame, width=10)
        self.can_send_repeat_entry.pack(side=tk.RIGHT, padx=5, pady=5)
        self.can_send_repeat_entry.insert(0, "1000")
        self.can_send_repeat_button = tk.Button(send_buttons_frame, text="Send Repeat", width=10, command=self.toggle_send_repeat)
        self.can_send_repeat_button.pack(side=tk.RIGHT, padx=0, pady=5)
        self.can_send_button = tk.Button(send_buttons_frame, text="Send", width=10, command=self.change_send_flag)
        self.can_send_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.can_send_repeat_button.config(state=tk.DISABLED)
        self.can_send_button.config(state=tk.DISABLED)
        
    def validate_and_move_focus(self, new_value, index):
        index = int(index)  # 문자열로 전달된 index를 정수로 변환
        if len(new_value) == 2:
            if index < len(self.dlc_entries) - 1:
                next_entry = self.dlc_entries[index + 1]
                next_entry.focus_set()
                next_entry.select_range(0, tk.END)  # 새로 포커스된 Entry의 내용을 드래그
        return len(new_value) <= 2
       
    def validate_hex(self, new_value):
        # Check if the new value is a valid hex string or empty
        if new_value == "":
            return True
        try:
            int(new_value, 16)
            return True
        except ValueError:
            return False
 
    def validate_dlc_entry(self, new_value):
        return len(new_value) <= 2
   
    def validate_can_id_length(self, new_value):
 
        return len(new_value) <= 8
 
    def validate_id_mask_entry(self, new_value):
        return new_value in ("", "0", "1")
 
    def show_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
 
    def show_hex(self):
        for item in self.tree.get_children():
            data = self.tree.item(item, "values")[4]
            hex_data = ' '.join(format(ord(c), '02X') for c in data)
            self.tree.set(item, column="Data", value=hex_data)
 
    def show_ascii(self):
        for item in self.tree.get_children():
            data = self.tree.item(item, "values")[4]
            try:
                ascii_data = ''.join(chr(int(h, 16)) for h in data.split())
                self.tree.set(item, column="Data", value=ascii_data)
            except ValueError:
                # Handle the case where data is not in hex format
                continue
       
    def clear_table(self):
        self.tree.delete(*self.tree.get_children())
        self.stop_update_view = True
        self.can_id_count.clear()
 
    def update_dlc_entries(self, event):
        if not self.hex_var.get():
            for entry in self.dlc_entries:
                entry.config(state=tk.DISABLED)
            return
 
        dlc_value = int(self.dlc_entry.get())
        for i, entry in enumerate(self.dlc_entries):
            if i < dlc_value:
                entry.config(state=tk.NORMAL)
            else:
                entry.config(state=tk.DISABLED)
 
    def toggle_ascii(self):
        if self.ascii_var.get():
            self.can_message_entry.config(state=tk.NORMAL)
            self.hex_checkbutton.config(state=tk.DISABLED)
        else:
            self.can_message_entry.config(state=tk.DISABLED)
            self.hex_checkbutton.config(state=tk.NORMAL)
 
    def toggle_hex(self):
        if self.hex_var.get():
            self.ascii_checkbutton.config(state=tk.DISABLED)
            self.dlc_entry.config(state="readonly")  # DLC 콤보박스 활성화
        else:
            self.ascii_checkbutton.config(state=tk.NORMAL)
            self.dlc_entry.config(state="readonly")  # DLC 콤보박스 비활성화
        self.update_dlc_entries(None)  # DLC 엔트리 업데이트
 
    def change_send_flag(self):
        self.clicked_send_btn = True

    def toggle_send_repeat(self):
        if self.can_send_repeat_button.cget("text") == "Send Repeat":
            try:
                repeat_interval = int(self.can_send_repeat_entry.get())
                if repeat_interval >= 140:
                    self.can_send_repeat_button.config(text="Send Stop")
                    self.clicked_send_repeat_btn = True
                else:
                    self.message_box.insert(tk.END, "The repeat value must be at least 140ms.\n")
            except ValueError:
                self.message_box.insert(tk.END, "Please enter a valid number.\n")
        else:
            self.can_send_repeat_button.config(text="Send Repeat")
            self.clicked_send_stop_btn = True
 
    def can_repeat_send(self):
        while self.serial_running:
            if self.clicked_send_repeat_btn:
                can_id = self.can_id_label_entry.get()
                try:
                    # Convert CAN ID from hex to decimal
                    can_id_decimal = int(can_id, 16)
                except ValueError:
                    self.message_box.insert(tk.END, "Invalid CAN ID. Please enter a valid hex value.\n")
                    return

                if self.ascii_var.get():
                    data = self.can_message_entry.get()
                    length = len(data)
                    ms = self.can_send_repeat_entry.get()
                    hex_data = ''.join(format(ord(c), '02X') for c in data)
                    message = f'can send {can_id_decimal} {length} {hex_data} repeat {ms}'
                    self.send_serial_can_data(message)
                else:
                    # Send only active dlc_entries
                    dlc_value = int(self.dlc_entry.get())
                    data = ''.join([entry.get() for entry in self.dlc_entries[:dlc_value] if entry.get()])
                    length = dlc_value
                    ms = self.can_send_repeat_entry.get()
                    message = f'can send {can_id_decimal} {length} {data} repeat {ms}'
                    self.send_serial_can_data(message)
                self.clicked_send_repeat_btn = False
            time.sleep(0.001)
            
    def can_stop_send(self):
        while self.serial_running:
            if self.clicked_send_stop_btn:
                self.send_serial_can_data("can stop")
                self.clicked_send_stop_btn = False
            time.sleep(0.001)
 
    def clear_serial_send_text(self):
        self.message_box.delete(0.0, tk.END)
       
    def send_serial_data(self):
        if hasattr(self, 'serial') and self.serial.is_open:
            message = self.serial_send_text.get()
            if not isinstance(message, str):
                message = str(message)
            message += '\n'
            try:
                for char in message:
                    self.serial.write(char.encode('utf-8'))
                    time.sleep(0.001)  # 0.1초 지연
                self.message_box.insert(tk.END, f"[SND] {message.strip()}\n")
            except UnicodeEncodeError:
                for char in message:
                    self.serial.write(char.encode('latin-1'))
                    time.sleep(0.001)
                self.message_box.insert(tk.END, f"[SND] (Latin-1): {message.strip()}\n")
            self.serial_send_text.delete(0, tk.END)
        else:
            self.message_box.insert(tk.END, f"Serial port is not open. Cannot send data.\n")
            
    def update_channel_info(self):
        channel_a = self.channel_var_a.get()
        channel_b = self.channel_var_b.get()
        channel_c = self.channel_var_c.get()
        
        channel_value = 0
        if channel_a:
            channel_value += 1
        if channel_b:
            channel_value += 2
        if channel_c:
            channel_value += 4

        if self.send_serial_can_info(f"can set 2 {channel_value}") == "Success":
            self.message_box.insert(tk.END, "-> Done.\n")
            self.message_box.yview_moveto(1.0)
            
    def update_baud_rate(self, event):
        baud_rate = self.nominal_baud_rate.get()
        if self.send_serial_can_info(f"can set 3 {baud_rate}") == "Success":
            self.message_box.insert(tk.END, "-> Done.\n")
            self.message_box.yview_moveto(1.0)
 
    def set_can_info(self):
        # 11비트 문자열을 받아옴
        id_mask = ''.join([entry.get() for entry in self.id_mask_entries][:11])
        id_acceptance = ''.join([entry.get() for entry in self.id_acceptance_entries][:11])
 
        # 이진수를 10진수로 변환
        id_mask_int = int(id_mask, 2)
        id_acceptance_int = int(id_acceptance, 2)
 
        # 2047로 제한
        id_mask_int = min(id_mask_int, 2047)
        id_acceptance_int = min(id_acceptance_int, 2047)
 
        # 제한된 값을 16진수로 변환
        id_mask_hex = format(id_mask_int, '03X')
        id_acceptance_hex = format(id_acceptance_int, '03X')
 
        if id_mask:
            self.send_serial_can_info(f"can set 5 {id_mask_hex}")
        if id_acceptance:
            self.send_serial_can_info(f"can set 6 {id_acceptance_hex}")
 
        self.message_box.insert(tk.END, "-> Done.\n")
 
    def can_send_message(self):
        while self.serial_running:
            if self.clicked_send_btn:
                can_id = self.can_id_label_entry.get()
                try:
                    # Convert CAN ID from hex to decimal
                    can_id_decimal = int(can_id, 16)
                except ValueError:
                    self.message_box.insert(tk.END, "Invalid CAN ID. Please enter a valid hex value.\n")
                    return

                if self.ascii_var.get():
                    data = self.can_message_entry.get()
                    length = len(data)
                    hex_data = ''.join(format(ord(c), '02X') for c in data)
                    message = f'can send {can_id_decimal} {length} {hex_data}'
                    self.send_serial_can_data(message)
                else:
                    # Send only active dlc_entries
                    dlc_value = int(self.dlc_entry.get())
                    data = ''.join([entry.get() for entry in self.dlc_entries[:dlc_value] if entry.get()])
                    length = dlc_value
                    message = f'can send {can_id_decimal} {length} {data}'
                    self.send_serial_can_data(message)
                self.clicked_send_btn = False
            time.sleep(0.001)
 
    def send_serial_can_info(self, message):
        if hasattr(self, 'serial') and self.serial.is_open:
            if not isinstance(message, str):
                message = str(message)
            message += '\n'
            try:
                for char in message:
                    self.serial.write(char.encode('utf-8'))
                    time.sleep(0.008)  # 0.1초 지연
                self.message_box.insert(tk.END, f"[SND] {message.strip()}\n")
                self.message_box.yview_moveto(1.0)
                return "Success"
            except UnicodeEncodeError:
                for char in message:
                    self.serial.write(char.encode('latin-1'))
                    time.sleep(0.008)
                self.message_box.insert(tk.END, f"[SND] (Latin-1): {message.strip()}\n")
                self.message_box.yview_moveto(1.0)
                return "Success"
        else:
            self.message_box.insert(tk.END, f"Serial port is not open. Cannot send data.\n")
            return "Fail"
 
    def send_serial_can_data(self, message):
        if hasattr(self, 'serial') and self.serial.is_open:
            if not isinstance(message, str):
                message = str(message)
            message += '\n'
            try:
                for char in message:
                    self.serial.write(char.encode('latin-1'))
                    time.sleep(0.0001)  # 0.1초 지연
                self.message_box.insert(tk.END, f"[SND] {message.strip()}\n")
                self.message_box.yview_moveto(1.0)
            except UnicodeEncodeError:
                for char in message:
                    self.serial.write(char.encode('utf-8'))
                    time.sleep(0.0001)
                self.message_box.insert(tk.END, f"[SND] {message.strip()}\n")
                self.message_box.yview_moveto(1.0)
        else:
            self.message_box.insert(tk.END, f"Serial port is not open. Cannot send data.\n")
 
    def connect_serial(self):
        com_port = self.com_port.get()
        baud_rate = int(self.baud_rate.get())
        stop_bits = float(self.stop_bit.get())
        parity = self.parity_bit.get()
        data_bits = int(self.data_bit.get())
 
        parity_dict = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }
 
        try:
            self.serial = serial.Serial(
                port=com_port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity_dict[parity],
                stopbits=stop_bits,
                timeout=1
            )
            self.message_box.insert(tk.END, f"Connected to {com_port} at {baud_rate} baud.\n")
            self.message_box.yview_moveto(1.0)
            self.send_button.config(state=tk.NORMAL)  # Enable send button when connected
            self.disconnect_button.config(state=tk.NORMAL)
            self.connect_button.config(state=tk.DISABLED)
            self.set_button.config(state=tk.NORMAL)
            self.can_send_button.config(state=tk.NORMAL)
            self.can_send_repeat_button.config(state=tk.NORMAL)
            self.serial_running = True
            self.read_thread = threading.Thread(target=self.read_serial)
            self.parse_thread = threading.Thread(target=self.parse_data_thread)
            self.log_thread = threading.Thread(target=self.log_data)
            self.can_send_thread = threading.Thread(target=self.can_send_message)
            self.can_repeat_send_thread = threading.Thread(target=self.can_repeat_send)
            self.can_stop_send_thread = threading.Thread(target=self.can_stop_send)
            self.read_thread.start()
            self.parse_thread.start()
            self.log_thread.start()
            self.can_send_thread.start()
            self.can_repeat_send_thread.start()
            self.can_stop_send_thread.start()
           
            # Update progress bar and status label
            self.progress['value'] = 100
            self.status_label.config(text="ON")

            # reconnect case
            if len(self.thrs_queue_dict) > 0:
                for key in self.thrs_queue_dict.keys():
                    threading.Thread(target=self.update_receive_view, args=(key, )).start()
        except Exception as e:
            self.message_box.insert(tk.END, f"Failed to connect: {e}\n")
 
    def read_serial(self):
        while self.serial_running:
            nowTimestamp = datetime.now()
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.readline()
                    if data:
                        timestamp = nowTimestamp.strftime("%H:%M:%S.%f")[:]  # 밀리초 단위까지 포맷팅
                        decoded_data = data.decode('latin-1')
                        # self.message_box.insert(tk.END, f"[{timestamp}]{decoded_data}")
                        if self.is_start_log(decoded_data):
                            self.message_box.insert(tk.END, f"{decoded_data}")
                            self.message_box.yview_moveto(1.0)
                        else:
                            self.data_queue.put((timestamp, decoded_data))  # Add data to the queue
            except serial.SerialException as e:
                self.message_box.insert(tk.END, f"Serial error: {e}\n")
                self.serial_running = False
                break
            except Exception as e:
                self.message_box.insert(tk.END, f"Unexpected error: {e}\n")
                self.serial_running = False
                break
            time.sleep(0.001)
            
    def is_start_log(self, message):
        # 특정 패턴의 로그만 필터링하는 로직
        log_patterns = [
            "[PMIO][PMIO_STR_OpenMsg",
            "Initialize System done",
            "Welcome to Telechips MCU BSP",
            "MCU BSP Version",
            "[SAL  ][FR_OSStart",
            "[PMIO][PMIO_STR_RecvMsgTask"
        ]
        return any(pattern in message for pattern in log_patterns)

    def parse_data_thread(self):
        while self.serial_running:
            try:
                timestamp, data = self.data_queue.get(timeout=1)  # Get data from the queue
                # print("parse_data_thread : ", self.data_queue.qsize())
                parts = data.split()
                if parts and parts[0] == ">":
                    parts = parts[1:]  # Remove the leading ">" if present
                if len(parts) >= 5 and parts[0] == "can" and parts[1] == "receive":
                    channel = parts[2]
                    if channel == "0":
                        charChannel = "A"
                    elif channel == "1":
                        charChannel = "B"
                    elif channel == "2":
                        charChannel = "C"
                    can_id = parts[3]
                    # decimal로 들어오는 can_id를 0xhex값으로 변환
                    hex_can_id = f"0x{format(int(can_id), '03X')}"
                    length = parts[4]
                    # Extract the data part correctly
                    raw_data = ''.join(parts[5:5+int(length)])
                    hex_data_part = ' '.join(re.findall('..', raw_data))
                    self.parse_and_insert_data(timestamp, charChannel, hex_can_id, length, hex_data_part)
            except queue.Empty:
                time.sleep(0.001)
                continue

    def parse_and_insert_data(self, timestamp, channel, can_id, length, hex_data):
        try:
            length = int(length)
            if length < 0 or length > 8:
                raise ValueError("Invalid length")
        except ValueError:
            return  # Skip if length is not between 0 and 8

        # timestamp = datetime.now().strftime("%H:%M:%S.%f")[:]  # 밀리초 단위까지 포맷팅

        # Update count for the CAN ID
        if can_id in self.can_id_count:
            self.can_id_count[can_id] += 1
        else:
            self.can_id_count[can_id] = 1
            self.thrs_queue_dict[can_id] = queue.Queue()    # create can_id thread's queue
            threading.Thread(target=self.update_receive_view, args=(can_id, )).start()  # start update thread

        self.log_queue.put((timestamp, channel, can_id, length, hex_data, self.can_id_count[can_id]))

        # print(f"put data - Timestamp: {timestamp}, CAN ID: {can_id}, Length: {length}, Data: {hex_data}, Count: {self.can_id_count[can_id]}")
        self.thrs_queue_dict[can_id].put_nowait((timestamp, channel, length, hex_data, self.can_id_count[can_id]))

    def update_receive_view(self, can_id):
        while self.serial_running:
            try:
                # print(f"self.thrs_queue_dict[{can_id}]'s queue size: {self.thrs_queue_dict[can_id].qsize()}")
                if self.stop_update_view:
                    self.stop_update_view = False
                    break
                if not self.thrs_queue_dict[can_id].empty():
                    timestamp, channel, length, hex_data, cnt = self.thrs_queue_dict[can_id].get_nowait()
                    if len(self.tree.get_children()) >= 40:
                        self.tree.delete(*self.tree.get_children())
                    # print(f"{timestamp}, {length}, {hex_data}")
                    # Insert new data
                    self.tree.insert("", "end", values=(timestamp, channel, can_id, length, hex_data, cnt))
                    # # Update existing item
                    # self.tree.item(item, values=(timestamp, can_id, length, hex_data, self.can_id_count[can_id]))
                    # # Auto-scroll to the bottom
                    self.tree.yview_moveto(1)
                # thrs_queue_dict size가 10개 이상이 queue에 쌓이면 초기화
                if self.thrs_queue_dict[can_id].qsize() >= 20:
                    self.thrs_queue_dict[can_id].queue.clear()
            except Exception as e:
                break
            time.sleep(0.001)

    def log_data(self):
        while self.serial_running:
            if not self.log_queue.empty():
                timestamp, channel, can_id, length, hex_data, count = self.log_queue.get()
                self.logger.info(f"Timestamp: {timestamp} | Channel: {channel} | ID: 0x{can_id} | Len: {length} | Data: {hex_data} | Count: {count}")
            for handler in self.logger.handlers:
                handler.flush()  # Ensure the log is written to the file immediately
            time.sleep(0.001)
        
    def on_closing(self):
        self.disconnect_serial()
        self.destroy()
        logging.shutdown()
 
    def disconnect_serial(self):
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial_running = False

            # Wait for threads to finish
            self.read_thread.join(timeout=0.5)
            self.parse_thread.join(timeout=0.5)
            self.log_thread.join(timeout=0.5)
            self.can_send_thread.join(timeout=0.5)
            self.can_repeat_send_thread.join(timeout=0.5)
            self.can_stop_send_thread.join(timeout=0.5)
            
            # Update UI elements
            self.send_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.NORMAL)
            self.set_button.config(state=tk.DISABLED)
            self.can_send_button.config(state=tk.DISABLED)
            self.can_send_repeat_button.config(state=tk.DISABLED)
            
            # Close the serial port
            self.serial.close()
            self.message_box.insert(tk.END, "Disconnected.\n")
            self.message_box.yview_moveto(1.0)
           
            # Update progress bar and status label
            self.progress['value'] = 0
            self.status_label.config(text="OFF")
        else:
            self.message_box.insert(tk.END, "No active connection to disconnect.\n")
            
    # def disconnect_serial(self):
    #     if hasattr(self, 'serial') and self.serial.is_open:
    #         self.serial_running = False
    #         self.message_box.insert(tk.END, "Stopping threads...\n")
    #         print("Stopping threads...")

    #         # Wait for threads to finish
    #         self.read_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "Read thread stopped.\n")
    #         print("Read thread stopped.")
    #         self.parse_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "Parse thread stopped.\n")
    #         print("Parse thread stopped.")
    #         self.log_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "Log thread stopped.\n")
    #         print("Log thread stopped.")
    #         self.can_send_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "CAN send thread stopped.\n")
    #         print("CAN send thread stopped.")
    #         self.can_repeat_send_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "CAN repeat send thread stopped.\n")
    #         print("CAN repeat send thread stopped.")
    #         self.can_stop_send_thread.join(timeout=1)
    #         self.message_box.insert(tk.END, "CAN stop send thread stopped.\n")
    #         print("CAN stop send thread stopped.")

    #         # Update UI elements
    #         self.send_button.config(state=tk.DISABLED)
    #         self.disconnect_button.config(state=tk.DISABLED)
    #         self.connect_button.config(state=tk.NORMAL)
    #         self.set_button.config(state=tk.DISABLED)
    #         self.can_send_button.config(state=tk.DISABLED)
    #         self.can_send_repeat_button.config(state=tk.DISABLED)
    #         print("UI elements updated.")

    #         # Close the serial port
    #         self.serial.close()
    #         self.message_box.insert(tk.END, "Disconnected.\n")
    #         print("Disconnected.")

    #         # Update progress bar and status label
    #         self.progress['value'] = 0
    #         self.status_label.config(text="OFF")
    #         print("Progress bar and status label updated.")
    #     else:
    #         self.message_box.insert(tk.END, "No active connection to disconnect.\n")
    #         print("No active connection to disconnect.")
 
if __name__ == "__main__":
    app = CANMonitorApp()
    app.mainloop()